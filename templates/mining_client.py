import base64
import os
import requests
import signal
import subprocess
import sys
import time
from urllib.parse import quote as url_quote
from traceback import print_exc


base_url = '{{ url_for("page_home", _external=True) }}'

miner_name = 'CHANGE_ME'

request_cooldown = 10
error_cooldown = 30
update_interval = 10


def do_mii_mine(id0, model, year, mii_data):
	cleanup_mining_files()
	with open('input.bin', 'wb') as mii_bin:
		mii_bin.write(mii_data)
	# bfCL
	args = [sys.executable, 'seedminer_launcher3.py', 'mii', model]
	if year:
		args.append(str(year))
	run_bfcl(id0, [sys.executable, 'seedminer_launcher3.py', 'gpu'])
	# check output
	if os.path.isfile('movable.sed'):
		print(f'Mining complete! Uploading movable...')
		upload_movable(id0)
	else:
		print(f'bfCL was not able to complete the mining job!')
	cleanup_mining_files()

def do_part1_mine(id0, part1_data):
	cleanup_mining_files()
	with open('movable_part1.sed', 'wb') as part1_bin:
		part1_bin.write(part1_data)
	# bfCL
	args = [sys.executable, 'seedminer_launcher3.py', 'gpu']
	run_bfcl(id0, args)
	# check output
	if os.path.isfile('movable.sed'):
		print(f'Mining complete! Uploading movable...')
		upload_movable(id0)
	else:
		print(f'bfCL was not able to complete the mining job!')
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
						cleanup_mining_files()
						return
		except KeyboardInterrupt:
			kill_process(process)
			print('Terminated bfCL')
			release_job(id0)
	except:
		print_exc()
		print('bfCL was not able to run correctly!')
		release_job(id0)

def cleanup_mining_files():
	to_remove = ['input.bin', 'movable.sed', 'movable_part1.sed']
	for file in to_remove:
		try:
			os.remove(file)
		except:
			pass

def update_job(id0):
	response = requests.get(f'{base_url}/api/update_job/{id0}')
	return response.json()['data'].get('status')

def release_job(id0):
	requests.get(f'{base_url}/api/release_job/{id0}')

def upload_movable(id0):
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


while True:
	try:
		response = requests.get(f'{base_url}/api/request_job?name={url_quote(miner_name)}').json()
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
	except:
		print_exc()
		print(f'Error contacting mining site, waiting {error_cooldown} seconds...')
		time.sleep(error_cooldown)
