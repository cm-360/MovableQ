import base64
import os
import requests
import signal
import subprocess
import sys
import time
from urllib.parse import quote as url_quote
from traceback import print_exc


# This is the URL of the mining coordination server you would like to use. Be
# sure to replace everything (including the curly braces) if you downloaded
# this script from GitHub. 
base_url = '{{ url_for("page_home", _external=True) }}'

# Enter a name for yourself. This name will be associated with your device on
# the mining server and shown on the leaderboard. Any jobs you claim will be
# associated with this name as well, so make sure its appropriate!
miner_name = 'CHANGE_ME'

# Choose which job types you are willing to mine. Note that mii mining jobs
# are typically much more demanding than part1 jobs, and can significantly
# stress your GPU. Part1 jobs are typically shorter, though this does not
# mean you will never claim a demanding/lengthy part1 job!
acceptable_job_types = [ 'part1', 'mii' ]

# values are in seconds
request_cooldown = 10
error_cooldown = 30
update_interval = 10


# benchmarking options
benchmark_target = 215
benchmark_filename = 'benchmark'
dry_run = False


def validate_benchmark():
	if not os.path.isfile(benchmark_filename):
		print('No existing bechmark found!')
		if do_benchmark():
			write_benchmark()

def write_benchmark():
	with open(benchmark_filename, 'w') as benchmark_file:
		benchmark_file.write(str(benchmark_target))

def erase_benchmark():
	try:
		os.remove(benchmark_filename)
	except:
		pass

def do_benchmark():
	global dry_run
	dry_run = True
	cleanup_mining_files()
	print('Benchmarking...')
	# write impossible part1
	with open('movable_part1.sed', 'wb') as part1_bin:
		content = b'\xFF\xEE\xFF'
		part1_bin.write(content)
		part1_bin.write(b'\0' * (0x1000 - len(content)))
	# run and time bfCL
	try:
		time_target = time.time() + benchmark_target
		args = [sys.executable, 'seedminer_launcher3.py', 'gpu', '0', '1']
		return_code = run_bfcl('fef0fef0fef0fef0fef0fef0fef0fef0', args)
		time_finish = time.time()
		if return_code != 101:
			print(f'Finished with an unexpected return code from bfCL: {return_code}')
		elif time_finish > time_target:
			print('Unfortunately, your graphics card is too slow to help mine.')
		else:
			print('Good news, your GPU is fast enough to help mine!')
			return True
	except BfclExecutionError:
		print('There was an error running bfCL! Please figure this out before joining the mining network.')
	finally:
		cleanup_mining_files()
		dry_run = False

def do_mii_mine(id0, model, year, mii_data, timeout=0):
	cleanup_mining_files()
	with open('input.bin', 'wb') as mii_bin:
		mii_bin.write(mii_data)
	try:
		# bfCL
		args = [sys.executable, 'seedminer_launcher3.py', 'mii', model]
		if year:
			args.append(str(year))
		run_bfcl(id0, args)
		# check output
		if os.path.isfile('movable.sed'):
			print(f'Mining complete! Uploading movable...')
			upload_movable(id0)
		else:
			print(f'bfCL was not able to complete the mining job!')
	finally:
		cleanup_mining_files()

def do_part1_mine(id0, part1_data, timeout=0):
	cleanup_mining_files()
	with open('movable_part1.sed', 'wb') as part1_bin:
		part1_bin.write(part1_data)
	try:
		# bfCL
		args = [sys.executable, 'seedminer_launcher3.py', 'gpu']
		run_bfcl(id0, args)
		# check output
		if os.path.isfile('movable.sed'):
			print(f'Mining complete! Uploading movable...')
			upload_movable(id0)
		else:
			print(f'bfCL was not able to complete the mining job!')
	finally:
		cleanup_mining_files()

def run_bfcl(id0, args):
	try:
		# set id0
		subprocess.call([sys.executable, 'seedminer_launcher3.py', 'id0', id0])
		# start mining
		process = subprocess.Popen(args)
		try:
			timer = 0
			while process.poll() is None:
				timer += 1
				time.sleep(1)
				if timer % update_interval == 0:
					status = update_job(id0)
					if status == 'canceled':
						print('Job canceled')
						kill_process(process)
						return
			check_bfcl_return_code(process.returncode)
		except KeyboardInterrupt:
			kill_process(process)
			print('Terminated bfCL')
			release_job(id0)
	except BfclReturnCodeError as e:
		fail_job(id0, f'{type(e).__name__}: {e}')
		return e.return_code
	except Exception as e:
		print_exc()
		print('bfCL was not able to run correctly!')
		message = f'{type(e).__name__}: {e}'
		fail_job(id0, message)
		raise BfclExecutionError(message) from e

def check_bfcl_return_code(return_code):
	if -1 == return_code:
		raise BfclReturnCodeError(return_code, 'invalid arguments (not verified, could be generic error)')
	elif 101 == return_code:
		raise BfclReturnCodeError(return_code, 'maximum offset reached without a hit')

def cleanup_mining_files():
	to_remove = ['input.bin', 'movable.sed', 'movable_part1.sed']
	for filename in to_remove:
		try:
			os.remove(filename)
		except:
			pass

def update_job(id0):
	if dry_run:
		return
	response = requests.get(f'{base_url}/api/update_job/{id0}')
	return response.json()['data'].get('status')

def release_job(id0):
	if dry_run:
		return
	requests.get(f'{base_url}/api/release_job/{id0}')

def fail_job(id0, note):
	if dry_run:
		return
	requests.post(
		f'{base_url}/api/fail_job/{id0}',
		json={'note': note}
	)

def upload_movable(id0):
	if dry_run:
		return
	with open('movable.sed', 'rb') as movable:
		response = requests.post(
			f'{base_url}/api/complete_job/{id0}',
			json={'movable': str(base64.b64encode(movable.read()), 'utf-8')}
		).json()

def kill_process(process):
	try:
		if os.name == 'nt':
			process.send_signal(signal.CTRL_C_EVENT)
		else:
			process.send_signal(signal.SIGINT)
		time.sleep(0.25)
	except KeyboardInterrupt:
		pass


class BfclReturnCodeError(Exception):

	def __init__(self, return_code, message):
		self.return_code = return_code
		self.message = message
		super().__init__(f'{return_code}, {message}')


class BfclExecutionError(Exception):

	def __init__(self, message):
		self.message = message
		super().__init__(message)


def run_client():
	global miner_name
	global acceptable_job_types
	# remind miner to change name variable
	if miner_name == 'CHANGE_ME':
		print('Please enter a name first.')
		return
	# sanitize variables
	miner_name = url_quote(miner_name)
	acceptable_job_types = ','.join(acceptable_job_types)
	# benchmark to find issues before claiming real jobs
	if not validate_benchmark():
		return
	# main mining loop
	while True:
		try:
			response = requests.get(f'{base_url}/api/request_job?name={miner_name}&types={acceptable_job_types}').json()
			if response['result'] == 'success':
				data = response['data']
				if data:
					job_type = data['type']
					if 'mii' == job_type:
						print('\nMii job received:')
						print(f'  ID0:   {data["id0"]}')
						print(f'  Model: {data["model"]}')
						print(f'  Year:  {data["year"]}')
						do_mii_mine(
							data['id0'],
							data['model'],
							data['year'],
							base64.b64decode(data['mii'])
						)
					elif 'part1' == job_type:
						print('\nPart1 job received:')
						print(f'  ID0:   {data["id0"]}')
						do_part1_mine(
							data['id0'],
							base64.b64decode(data['part1'])
						)
					else:
						print(f'Unknown job type "{job_type}" received, ignoring...')
				else:
					print(f'No mining jobs, waiting {request_cooldown} seconds...', end='\r')
			time.sleep(request_cooldown)
		except KeyboardInterrupt:
			should_exit = input('\nWould you like to exit? (y/n): ')
			if should_exit.lower().startswith('y'):
				break
		except BfclExecutionError as e:
			# errors not arising from return codes mean a bigger issue
			erase_benchmark()
			break
		except:
			print_exc()
			print(f'Error contacting mining site, waiting {error_cooldown} seconds...')
			time.sleep(error_cooldown)

if __name__ == '__main__':
	run_client()