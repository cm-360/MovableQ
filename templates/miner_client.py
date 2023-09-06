import base64
import os
import requests
import signal
import subprocess
import sys
import time
from urllib.parse import quote as url_quote
from traceback import print_exc


base_url = '{{ url_for("page_home", _external=True) }}api'

request_cooldown = 10
error_cooldown = 30
update_interval = 10

miner_name = 'CHANGE_ME'


def do_mii_mine(id0, model, year, mii_data):
	cleanup_mining_files()
	with open('input.bin', 'wb') as mii_bin:
		mii_bin.write(mii_data)
	try:
		# set id0
		subprocess.call([sys.executable, 'seedminer_launcher3.py', 'id0', id0])
		# mining args 
		args = [sys.executable, 'seedminer_launcher3.py', 'mii', model]
		if year:
			args.append(str(year))
		# start mining
		process = subprocess.Popen(args)
		try:
			timer = 0
			while process.poll() is None:
				timer += 1
				time.sleep(1)
				if timer % update_interval == 0:
					response = requests.get(f'{base_url}/update_job/{id0}')
					status = response.json()['data'].get('status')
					if status == 'canceled':
						print('Job canceled')
						kill_process(process)
						cleanup_mining_files()
						return
		except KeyboardInterrupt:
			kill_process(process)
			print('Terminated bfCL')
	except:
		print_exc()
		print('bfCL was not able to run correctly!')
	# check output
	if os.path.isfile('movable.sed'):
		print(f'Mining complete! Uploading movable...')
		upload_movable(id0)
	else:
		print(f'bfCL was not able to complete the mining job!')
	cleanup_mining_files()

def cleanup_mining_files():
	for file in ['input.bin', 'movable.sed']:
		try:
			os.remove(file)
		except:
			pass

def upload_movable(id0):
	with open('movable.sed', 'rb') as movable:
		response = requests.post(
			f'{base_url}/complete_job/{id0}',
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
		response = requests.get(f'{base_url}/request_job?name={url_quote(miner_name)}').json()
		if response['result'] == 'success':
			data = response['data']
			if data:
				print('\nJob received:')
				print(f'  ID0:   {data["id0"]}')
				print(f'  Model: {data["model"]}')
				print(f'  Year:  {data["year"]}')
				do_mii_mine(
					data['id0'],
					data['model'],
					data['year'],
					base64.b64decode(data['mii'])
				)
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
