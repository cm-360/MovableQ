import base64
import os
import requests
import signal
import struct
import subprocess
import sys
import time
from binascii import hexlify, unhexlify
from urllib.parse import quote as url_quote
from traceback import print_exc


# This should be set by the server when downloaded. Only change if you know
# what you are doing!
client_version = '{{ client_version }}'

# This is the URL of the mining coordination server you would like to use. It
# should be set automatically when downloading from the mining website. Only
# change this if you know what you are doing!
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

# set this variable to "True" (without the quotes) if you want to use less of your gpu while mining
# your hash rate will decrease by a bit
force_reduced_work_size = False

# values are in seconds
request_cooldown = 10
error_cooldown = 30
update_interval = 10


# benchmarking options
benchmark_target = 215
benchmark_filename = 'benchmark'
dry_run = False


# LFCS bruteforce starting points from seedminer_launcher3.py by zoogie
# https://github.com/zoogie/seedminer/blob/master/seedminer/seedminer_launcher3.py#L140-L184
lfcs_starts_old = {
	2011: 0x01000000,
	2012: 0x04000000,
	2013: 0x07000000,
	2014: 0x09000000,
	2015: 0x09800000,
	2016: 0x0A000000,
	2017: 0x0A800000
}
lfcs_starts_new = {
	2014: 0x00800000,
	2015: 0x01800000,
	2016: 0x03000000,
	2017: 0x04000000
}
# default starting points
lfcs_default_old = 0x0B000000 // 2
lfcs_default_new = 0x05000000 // 2

# lfcs/msed3 relationship database filenames 
lfcs_db_filename_old = 'saves/old-v2.dat'
lfcs_db_filename_new = 'saves/new-v2.dat'
# lfcses/msed3s from old/new databases
db_lfcses_old = []
db_lfcses_new = []
db_msed3s_old = []
db_msed3s_new = []


# Helper functions from seedminer_launcher3.py by zoogie
# https://github.com/zoogie/seedminer/blob/master/seedminer/seedminer_launcher3.py#L51-L84
def bytes2int(s):
	n = 0
	for i in range(4):
		n += ord(s[i:i+1]) << (i * 8)
	return n

def int2bytes(n):
	s = bytearray(4)
	for i in range(4):
		s[i] = n & 0xFF
		n = n >> 8
	return s

# swap the endian-ness of input data (reverses bytes)
def byteswap(data):
	return data[::-1]

# invert the endian-ness of every n bytes of data
def byteswap_each_n(data, n):
	if len(data) % n != 0:
		raise ValueError(f'Input data length must be a multiple of {n}')
	swapped_data = bytearray()
	for i in range(0, len(data), n):
		swapped_data.extend(byteswap(data[i:i+n]))
	return swapped_data

# invert the endian-ness of a 32-bit integer
def endian4(n):
	return (n & 0xFF000000) >> 24 | (n & 0x00FF0000) >> 8 | (n & 0x0000FF00) << 8 | (n & 0x000000FF) << 24

# Modified from generate_part2 @ seedminer_launcher3.py by zoogie
# https://github.com/zoogie/seedminer/blob/master/seedminer/seedminer_launcher3.py#L197-L273
def generate_part2(seed: bytes, *id0s) -> bytes:
	# max 64 id0s
	if len(id0s) > 64:
		raise ValueError('Maximum of 64 ID0s allowed')
	# pad seed to 12 bytes, full seed should be 16 but is not needed
	if len(seed) < 12:
		seed += b'\x00' * (12 - len(seed))
	# determine console type
	if seed[4:5] == b'\x02':
		print('New3DS msed')
		is_new = True
	elif seed[4:5] == b'\x00':
		print('Old3DS msed - this can happen on a New3DS')
		is_new = False
	else:
		raise ValueError('Invalid flag')
	# estimate msed3 value
	msed3_estimate = get_msed3_estimate(seed, is_new)
	print(f'LFCS	  : {hex(bytes2int(seed[0:4]))}')
	print(f'msed3 est : {hex(msed3_estimate)}')
	# add id0 hashes
	hash_final = b''
	for i in range(len(id0s)):
		hash_init = unhexlify(id0s[i])
		hash_single = byteswap_each_n(hash_init, 4)
		print(f'ID0 hash {i}: {hexlify(hash_single).decode("ascii")}')
		hash_final += hash_single
	print(f'Hash total: {len(id0s)}')
	return seed[0:12] + int2bytes(msed3_estimate) + hash_final

# Modified from getmsed3estimate @ seedminer_launcher3.py by zoogie
# https://github.com/zoogie/seedminer/blob/master/seedminer/seedminer_launcher3.py#L87-L114
def get_msed3_estimate(seed: bytes, is_new: bool):
	if is_new:
		newbit = 0x80000000
		lfcses = db_lfcses_new
		msed3s = db_msed3s_new
	else:
		newbit = 0x00000000
		lfcses = db_lfcses_old
		msed3s = db_msed3s_old

	lfcses_size = len(lfcses)
	msed3s_size = len(msed3s)

	n = bytes2int(seed[0:4])
	
	# find estimate from graph
	for i in range(lfcses_size):
		if n < lfcses[i]:
			xs = (n - lfcses[i-1])
			xl = (lfcses[i] - lfcses[i-1])
			y = msed3s[i - 1]
			yl = (msed3s[i] - msed3s[i-1])
			ys = ((xs * yl) // xl) + y
			# err_correct = ys
			return ((n // 5) - ys) | newbit
	return ((n // 5) - msed3s[msed3s_size-1]) | newbit

def get_lfcs_start_and_flags(model, year):
	if 'old' == model:
		model_bytes = b'\x00\x00'
		start_lfcs = lfcs_starts_old.get(year, lfcs_default_old)
	elif 'new' == model:
		model_bytes = b'\x02\x00'
		start_lfcs = lfcs_starts_new.get(year, lfcs_default_new)
	else:
		raise ValueError('Invalid model')
	return start_lfcs, model_bytes

# Calculates the max offset bfCL should check for a given LFCS
# Adapted from @eip618's BFM autolauncher script
def get_max_offset(lfcs_bytes):
	lfcs = int.from_bytes(lfcs_bytes, byteorder='little')
	is_new = lfcs >> 32
	lfcs &= 0xFFFFFFF0
	lfcs |= 0x8

	# determine offsets/distances and load LFCSes for appropriate console type
	if 2 == is_new:
		max_offsets = [     16,      16,      20]
		distances   = [0x00000, 0x00100, 0x00200]
		lfcses = db_lfcses_new
	elif 0 == is_new:
		max_offsets = [     18,      18,      20]
		distances   = [0x00000, 0x00100, 0x00200]
		lfcses = db_lfcses_old
	else:
		raise ValueError('LFCS high u32 is not 0 or 2')

	# compare given LFCS to saved list and find smallest distance estimate
	lfcses_size = len(lfcses)
	distance = lfcs - lfcses[lfcses_size-1]
	for i in range(1, lfcses_size - 1):
		if lfcs < lfcses[i]:
			distance = min(lfcs - lfcses[i-1], lfcses[i+1] - lfcs)
			break

	# print('Distance: %08X' % distance)
	# get largest max offset for calulcated distance estimate
	i = 0
	for d in distances:
		if distance < d:
			return max_offsets[i-1] + 10
		i += 1
	return max_offsets[len(distances) - 1] + 10


def validate_benchmark():
	if os.path.isfile(benchmark_filename):
		print('Skipping benchmark')
		return True
	else:
		print('No existing bechmark found!')
		if do_benchmark():
			write_benchmark()
			return True

def write_benchmark():
	with open(benchmark_filename, 'w') as benchmark_file:
		benchmark_file.write(str(benchmark_target))

def erase_benchmark():
	try:
		os.remove(benchmark_filename)
	except:
		pass

# Modified from do_gpu @ seedminer_launcher3.py by zoogie
# https://github.com/zoogie/seedminer/blob/master/seedminer/seedminer_launcher3.py#L394-L402
def do_benchmark():
	global dry_run
	dry_run = True
	cleanup_mining_files()
	print('Benchmarking...')
	# run and time bfCL
	try:
		# impossible part1
		buf = generate_part2(b'\xFF\xEE\xFF', 'fef0fef0fef0fef0fef0fef0fef0fef0')
		time_target = time.time() + benchmark_target
		# bfCL
		bfcl_args = [
			'msky',
			hexlify(buf[:16]).decode('ascii'), # keyy
			hexlify(buf[16:32]).decode('ascii'), # id0
			f'{endian4(0):08X}',
			f'{endian4(5):08X}'
		]
		return_code = run_bfcl('benchmark', bfcl_args)
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

def do_mii_mine(model, year, system_id, timeout=0):
	cleanup_mining_files()
	try:
		start_lfcs, model_bytes = get_lfcs_start_and_flags(model, year)
		# bfCL
		bfcl_args = [
			'lfcs',
			f'{endian4(start_lfcs):08X}'
			hexlify(model_bytes).decode('ascii'),
			system_id,
			f'{endian4(0):08X}'
		]
		run_bfcl(system_id, bfcl_args)
		# check output
		if os.path.isfile('movable_part1.sed'):
			print(f'Mining complete! Uploading movable_part1...')
			upload_lfcs(system_id)
		else:
			print(f'bfCL was not able to complete the mining job!')
	finally:
		cleanup_mining_files()


# Modified from do_gpu @ seedminer_launcher3.py by zoogie
# https://github.com/zoogie/seedminer/blob/master/seedminer/seedminer_launcher3.py#L394-L402
def do_part1_mine(id0, lfcs, timeout=0):
	cleanup_mining_files()
	try:
		lfcs_bytes = unhexlify(lfcs)
		max_offset = get_max_offset(lfcs_bytes)
		print(f'Using maximum offset: {max_offset}')
		part2 = generate_part2(lfcs_bytes, id0)
		# bfCL
		bfcl_args = [
			'msky',
			hexlify(part2[:16]).decode('ascii'), #keyy
			hexlify(part2[16:32]).decode('ascii'), # mid0
			f'{endian4(0):08X}',
			f'{endian4(max_offset):08X}'
		]
		run_bfcl(id0, bfcl_args)
		# check output
		if os.path.isfile('movable.sed'):
			print(f'Mining complete! Uploading movable...')
			upload_movable(id0)
		else:
			print(f'bfCL was not able to complete the mining job!')
	finally:
		cleanup_mining_files()

def run_bfcl(job_key, args, rws=force_reduced_work_size):
	try:
		bfcl_args = [
			('bfcl' if os.name == 'nt' else './bfcl'),
			*args,
			*(['rws'] if rws else ['sws', 'sm'])
		]
		print(f'bfCL args: {" ".join(bfcl_args)}')
		# start mining
		process = subprocess.Popen(bfcl_args)
		try:
			timer = 0
			while process.poll() is None:
				timer += 1
				time.sleep(1)
				if timer % update_interval == 0:
					status = update_job(job_key)
					if status == 'canceled':
						print('Job canceled')
						kill_process(process)
						return 0
			# Help wanted for a better way of catching an exit code of '-5'
			if not rws and (process.returncode == 251 or process.returncode == 0xFFFFFFFB):
				time.sleep(3)  # Just wait a few seconds so we don't burn out our graphics card
				return run_bfcl(job_key, args, True)
			else:
				check_bfcl_return_code(process.returncode)
		except KeyboardInterrupt:
			kill_process(process)
			print('Terminated bfCL')
			release_job(job_key)
	except BfclReturnCodeError as e:
		fail_job(job_key, f'{type(e).__name__}: {e}')
		return e.return_code
	except Exception as e:
		print_exc()
		print('bfCL was not able to run correctly!')
		message = f'{type(e).__name__}: {e}'
		fail_job(job_key, message)
		raise BfclExecutionError(message) from e
	return 0
args
def check_bfcl_return_code(return_code):
	if -1 == return_code:
		raise BfclReturnCodeError(return_code, 'invalid arguments (not verified, could be generic error)')
	elif 101 == return_code:
		raise BfclReturnCodeError(return_code, 'maximum offset reached without a hit')

def cleanup_mining_files():
	to_remove = ['movable.sed', 'movable_part1.sed']
	for filename in to_remove:
		try:
			os.remove(filename)
		except:
			pass

def request_job():
	if dry_run:
		return
	request_params = '&'.join([
		f'version={client_version}',
		f'name={miner_name}',
		f'types={acceptable_job_types}'
	])
	response = requests.get(f'{base_url}/api/request_job?{request_params}').json()
	result = response['result']
	if 'success' != result:
		error_message = response['message']
		print(f'Error from server: {error_message}')
		return
	return response['data']

def do_job(job):
	job_type = job['type']
	if 'mii' == job_type:
		print('Mii job received:')
		print(f'  Model: {job["model"]}')
		print(f'  Year:  {job["year"]}')
		print(f'  SysID: {job["system_id"]}')
		do_mii_mine(
			job['model'],
			job['year'],
			job['system_id']
		)
	elif 'part1' == job_type:
		print('Part1 job received:')
		print(f'  ID0:  {job["id0"]}')
		print(f'  LFCS: {job["lfcs"]}')
		do_part1_mine(
			job['id0'],
			job['lfcs']
		)
	else:
		print(f'Unknown job type "{job_type}" received, ignoring...')

def update_job(key):
	if dry_run:
		return
	response = requests.get(f'{base_url}/api/update_job/{key}')
	return response.json()['data'].get('status')

def release_job(key):
	if dry_run:
		return
	requests.get(f'{base_url}/api/release_job/{key}')

def fail_job(key, note):
	if dry_run:
		return
	requests.post(
		f'{base_url}/api/fail_job/{key}',
		json={'note': note}
	)

# we actually upload only the keyY, but whatever
def upload_movable(id0):
	if dry_run:
		return
	with open('movable.sed', 'rb') as movable_file:
		response = requests.post(
			f'{base_url}/api/complete_job/{id0}',
			json = {
				'result': str(base64.b64encode(movable_file.read()[0x110:0x120]), 'utf-8'),
				'format': 'b64'
			}
		).json()

def upload_lfcs(system_id):
	if dry_run:
		return
	with open('movable_part1.sed', 'rb') as part1_file:
		response = requests.post(
			f'{base_url}/api/complete_job/{system_id}',
			json = {
				'result': str(base64.b64encode(part1_file.read()[:8]), 'utf-8'),
				'format': 'b64'
			}
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


def load_lfcs_dbs():
	global db_lfcses_old
	global db_lfcses_new
	global db_msed3s_old
	global db_msed3s_new
	db_lfcses_old, db_msed3s_old = load_lfcs_db(lfcs_db_filename_old)
	db_lfcses_new, db_msed3s_new = load_lfcs_db(lfcs_db_filename_new)

def load_lfcs_db(lfcs_db_filename: str):
	with open(lfcs_db_filename, 'rb') as lfcs_db_file:
		lfcs_db_data = lfcs_db_file.read()
		lfcs_db_len = len(lfcs_db_data) // 8
		# unpack lfcses/msed3s from database
		lfcses = []
		msed3s = []
		for i in range(lfcs_db_len):
			pair_index = i * 8
			lfcses.append(struct.unpack('<I', lfcs_db_data[pair_index:pair_index+4])[0])
			msed3s.append(struct.unpack('<I', lfcs_db_data[pair_index+4:pair_index+8])[0])
		return lfcses, msed3s


def run_client():
	global miner_name
	global acceptable_job_types
	# remind miner to change name variable
	if miner_name == 'CHANGE_ME':
		print('Please enter a name first.')
		return
	# initialize
	print('Loading LFCS/msed3 databases')
	load_lfcs_dbs()
	# sanitize variables
	miner_name = url_quote(miner_name)
	acceptable_job_types = ','.join(acceptable_job_types)
	# benchmark to find issues before claiming real jobs
	if not validate_benchmark():
		return
	# main mining loop
	while True:
		try:
			try:
				job = request_job()
				if job:
					print() # wait message carriage return fix
					do_job(job)
				else:
					print(f'No mining jobs, waiting {request_cooldown} seconds...', end='\r')
					time.sleep(request_cooldown)
			except Exception as e:
				print() # wait message carriage return fix
				raise e
		except KeyboardInterrupt:
			should_exit = input('Would you like to exit? (y/n): ')
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
