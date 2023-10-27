#!/usr/bin/env python3

import base64
import io
import json
import os
from functools import wraps
from logging.config import dictConfig

# Flask server
from flask import Flask, request, render_template, make_response, send_from_directory, g
from werkzeug.exceptions import HTTPException
from werkzeug.middleware.proxy_fix import ProxyFix

# QR decoding
from pyzbar.pyzbar import decode as qr_decode
from PIL import Image

# AES decryption
from binascii import hexlify, unhexlify
try:    # pycryptodomex
    from Cryptodome.Cipher import AES
except: # pycryptodome
    from Crypto.Cipher import AES

# .env configuration
from dotenv import load_dotenv

# MovableQ modules
from jobs import JobManager, Job, FcLfcsJob, MiiLfcsJob, MsedJob, read_movable, count_mseds_mined, count_lfcses_mined, count_lfcses_dumped
from validators import is_job_key, is_id0, is_system_id, is_friend_code, is_blacklisted_friend_code, validate_job_result, enforce_client_version


# AES keys are loaded from .env
slot0x31KeyN = None

# logging config
dictConfig({
    'version': 1,
    'formatters': {'default': {
        'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
    }},
    'handlers': {'wsgi': {
        'class': 'logging.StreamHandler',
        'stream': 'ext://flask.logging.wsgi_errors_stream',
        'formatter': 'default'
    }},
    'root': {
        'level': 'INFO',
        'handlers': ['wsgi']
    }
})

# flask app
app = Flask(__name__)
app.wsgi_app = ProxyFix(
    app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1
)
app.config['TEMPLATES_AUTO_RELOAD'] = True

# job manager
manager = JobManager()

# clients info
mining_client_filename = 'mining_client.py'
client_types = {
    'miiner': {
        'version': '2.1.1-alpha',
        'allowed': {'mii-lfcs', 'msed'}
    },
    'friendbot': {
        'version': '1.0.0',
        'allowed': {'fc-lfcs'}
    }
}

# completion totals
mseds_mined = 0
lfcses_mined = 0
lfcses_dumped = 0


# authentication

def check_auth(username, password):
    return username == os.getenv('ADMIN_USER', 'admin') and password == os.getenv('ADMIN_PASS', 'INSECURE')

# https://stackoverflow.com/questions/22919182/flask-http-basicauth-how-does-it-work
def login_required(f):
    @wraps(f)
    def wrapped_view(**kwargs):
        auth = request.authorization
        if not (auth and check_auth(auth.username, auth.password)):
            return ('Unauthorized', 401, {
                'WWW-Authenticate': 'Basic realm="Login Required"'
            })
        return f(**kwargs)
    return wrapped_view


# frontend routes

@app.route('/')
def page_home():
    return render_template('pages/home.html')

@app.route('/method/<method_name>')
def page_force_method(method_name):
    if method_name not in ['fc', 'mii']:
        return error(f'Unknown method {method_name}')
    return render_template('pages/home.html')

@app.route('/volunteer')
def page_volunteer():
    return render_template('pages/volunteer.html')

@app.route('/admin')
@login_required
def page_admin():
    return render_template('pages/admin.html')

@app.route('/js/<path:filename>')
def serve_js(filename: str):
    response = make_response(render_template('js/' + filename))
    response.headers.set('Content-Type', 'text/javascript')
    return response

@app.route('/favicon.png')
def serve_favicon():
    return send_from_directory('static', 'favicon.png')

@app.route('/get_mining_client')
def get_mining_client():
    client_version = f'miiner-{client_types["miiner"]["version"]}'
    miner_name = request.args.get('name', 'CHANGE_ME')
    response = make_response(render_template(mining_client_filename, client_version=client_version, miner_name=miner_name))
    response.headers.set('Content-Type', 'application/octet-stream')
    response.headers.set('Content-Disposition', 'attachment', filename=mining_client_filename)
    return response

@app.route('/download_movable/<id0>')
def download_movable(id0: str):
    if not is_id0(id0):
        return error('Invalid ID0')
    movable = read_movable(id0)
    if not movable:
        return error('Movable not found', 404)
    response = make_response(movable)
    response.headers.set('Content-Type', 'application/octet-stream')
    response.headers.set('Content-Disposition', 'attachment', filename=f'movable.sed')
    return response


# api routes

@app.route('/api/submit_job_chain', methods=['POST'])
def api_submit_job_chain():
    submission = request.get_json(silent=True)
    if not submission:
        return error('Missing request JSON')
    try:
        # parse and submit chain
        chain = parse_job_chain(submission)
        chain_keys = [j.key for j in chain]
        manager.submit_job_chain(chain, overwrite_canceled=True)
        # if end job is already done, whole chain is discarded, so only do things if it's not
        end_job = chain[-1]
        if not end_job.is_already_done():
            # queue jobs with no prerequisites
            first_job = chain[0]
            if first_job.is_ready() and not end_job.is_already_done():
                manager.queue_job(first_job.key)
            # complete jobs with existing result
            manager.autocomplete_jobs(chain_keys)
        # return job keys to submitter
        app.logger.info(f'{log_prefix(", ".join(chain_keys))} submitted')
        return success(chain_keys)
    except InvalidSubmissionFieldError as e:
        return error(str(e))

@app.route('/api/submit_mii_lfcs_job', methods=['POST'])
def api_submit_mii_lfcs_job():
    return error('Not implemented')

@app.route('/api/submit_fc_job', methods=['POST'])
def api_submit_fc_lfcs_job():
    return error('Not implemented')

@app.route('/api/submit_msed_job', methods=['POST'])
def api_submit_msed_job():
    return error('Not implemented')

@app.route('/api/request_job')
def api_request_job():
    release_dead_jobs()
    # worker info
    worker_ip = get_request_ip()
    worker_name = request.args.get('name', worker_ip)
    # restrict clients
    client_version = request.args.get('version')
    requested_types = request.args.get('types')
    app.logger.info(f'{log_prefix()} {worker_name} requests work: version {client_version}, wants {requested_types}')
    if requested_types:
        requested_types = set(requested_types.split(','))
    allowed_types = enforce_client_version(client_types, client_version, requested_types)
    # check for and assign jobs
    job = manager.request_job(allowed_types, worker_name, worker_ip, client_version)
    if job:
        app.logger.info(f'{log_prefix(job.key, job.subkey)} assigned to {worker_name}')
        return success(dict(job))
    else:
        return success()

@app.route('/api/release_job/<key>')
@app.route('/api/release_job/<key>/<subkey>')
def api_release_job(key: str, subkey: str = None):
    if not is_job_key(key):
        return error('Invalid Job Key')
    manager.release_job(key, subkey)
    app.logger.info(f'{log_prefix(key, subkey)} released')
    return success()

@app.route('/api/check_job_statuses/<job_keys>')
def api_check_job_statuses(job_keys: str):
    statuses = []
    for job_key in job_keys.split(','):
        if not is_job_key(job_key):
            return error('Invalid Job Key')
        job_status = {
            'key': job_key,
            'status': manager.check_job_status(job_key)
        }
        if manager.job_exists(job_key):
            job_status['type'] = manager.get_job(job_key).type
            job_status['mining_stats'] = manager.get_mining_stats(job_key)
        statuses.append(job_status)
    return success(statuses)

@app.route('/api/update_job/<key>')
@app.route('/api/update_job/<key>/<subkey>')
def api_update_job(key: str, subkey: str = None):
    if not is_job_key(key):
        return error('Invalid Job Key')
    app.logger.info(f'{log_prefix(key, subkey)} still mining')
    if manager.update_job(key, subkey, worker_ip=get_request_ip()):
        return success()
    else:
        return success({'status': 'canceled'})

@app.route('/api/cancel_job/<key>')
def api_cancel_job(key: str):
    trim_canceled_jobs()
    if not is_job_key(key):
        return error('Invalid Job Key')
    manager.cancel_job(key)
    app.logger.info(f'{log_prefix(key)} canceled')
    return success()

@app.route('/api/reset_job/<key>')
def api_reset_job(key: str):
    if not is_job_key(key):
        return error('Invalid Job Key')
    manager.reset_job(key)
    app.logger.info(f'{log_prefix(key)} reset')
    return success()

@app.route('/api/complete_job/<key>', methods=['POST'])
@app.route('/api/complete_job/<key>/<subkey>', methods=['POST'])
def api_complete_job(key: str, subkey: str = None):
    global mseds_mined, lfcses_mined, lfcses_dumped
    if not is_job_key(key):
        return error('Invalid Job Key')
    # get raw result data
    result = None
    try:
        result_format = request.json['format']
        if 'b64' == result_format:
            result = base64.b64decode(request.json['result'])
        elif 'hex' == result_format:
            result = unhexlify(request.json['result'])
        elif 'none' == result_format:
            pass  # specifically for lfcs offset no hit
        else:
            raise ValueError(f'Unknown result format {result_format}')
    except KeyError as e:
        raise KeyError(f'Missing parameter {e}')
    # validate result
    job_type = manager.get_job(key).type
    if not validate_job_result(job_type, result, key, subkey):
        app.logger.warning(f'{log_prefix(key, subkey)} got faulty result')
        manager.release_job(key, subkey)
        return error('Faulty result')
    # complete job
    manager.complete_job(key, result, subkey)
    app.logger.info(f'{log_prefix(key, subkey)} completed')
    # update counter
    if 'msed' == job_type:
        mseds_mined += 1
    elif 'mii-lfcs' == job_type:
        lfcses_mined += 1
    elif 'fc-lfcs' == job_type:
        lfcses_dumped += 1
    return success()

@app.route('/api/fail_job/<key>', methods=['POST'])
@app.route('/api/fail_job/<key>/<subkey>', methods=['POST'])
def api_fail_job(key: str, subkey: str = None):
    if not is_job_key(key):
        return error('Invalid Job Key')
    manager.fail_job(key, subkey, request.json.get('note'))
    app.logger.info(f'{log_prefix(key, subkey)} failed')
    return success()

@app.route('/api/list_claimed_jobs')
def api_list_claimed_jobs():
    worker_name = request.args.get("name")
    if not worker_name:
        return error("No worker name provided")
    # maybe fallback to matching by ip?
    # downside would be slower and potential for returning wrong job types
    # if there was a friendbot and miner running on the same ip unless a type is also provided
    claimed = []
    for job in manager.list_jobs(status_filter="working"):
        if job.get_assignee_name() == worker_name:
            job.update()  # update job to avoid server timing it out
            claimed.append(dict(job))
    return success({"jobs": claimed})

@app.route('/api/check_network_stats')
def api_check_network_stats():
    return success({
        'waiting': manager.count_jobs('waiting'),
        'working': manager.count_jobs('working'),
        'workers': manager.count_workers(active_only=True),
        'friendbots': manager.count_friendbots(active_only=True),
        'miners': manager.count_miners(active_only=True),
        'mseds_mined': mseds_mined
    })

@app.route('/api/admin/list_jobs')
@login_required
def api_admin_list_jobs():
    with manager.lock:
        return success({
            'jobs': [dict(j) for j in manager.list_jobs()],
            'queue': list(manager.wait_queue)
        })

@app.route('/api/admin/list_workers')
@login_required
def api_admin_list_workers():
    with manager.lock:
        return success({
            'workers': [dict(m) for m in manager.list_workers()]
        })

@app.route('/api/admin/list_miners')
@login_required
def api_admin_list_miners():
    with manager.lock:
        return success({
            'miners': [dict(m) for m in manager.list_miners()]
        })

@app.route('/api/admin/list_friendbots')
@login_required
def api_admin_list_friendbots():
    with manager.lock:
        return success({
            'friendbots': [dict(m) for m in manager.list_friendbots()]
        })

# flask helpers

def success(data={}):
    response_json = json.dumps({
        'result': 'success',
        'data': data
    })
    return make_response(response_json, 200)

def error(message, code=400):
    response_json = json.dumps({
        'result': 'error',
        'message': message
    })
    return make_response(response_json, code)

def log_prefix(key=None, subkey=None) -> str:
    prefix = '(' + get_request_ip() + ')'
    if key:
        prefix += f' {key}'
    if subkey:
        prefix += f'-{subkey}'
    return prefix

@app.errorhandler(Exception)
def handle_exception(e: Exception):
    # pass through HTTP errors
    if isinstance(e, HTTPException):
        return e
    app.logger.error(f'{log_prefix()} caught exception')
    app.logger.exception(e)
    return error(f'{type(e).__name__}: {e}', code=500)


# manager action wrappers

def release_dead_jobs():
    released = manager.release_dead_jobs()
    if released:
        app.logger.info('automatically released jobs:')
        for key in released:
            app.logger.info(f'\t{key}')

def trim_canceled_jobs():
    deleted = manager.trim_canceled_jobs()
    if deleted:
        app.logger.info('automatically deleted jobs:')
        for key in deleted:
            app.logger.info(f'\t{key}')


# helper functions

def parse_job_chain(chain_data) -> list[Job]:
    jobs = []
    previous_job = None
    entry_index = 0
    for entry in chain_data:
        try:
            entry_type = entry['type']
            if 'mii-lfcs' == entry_type:
                jobs.append(parse_mii_lfcs_job(entry))
            elif 'fc-lfcs' == entry_type:
                jobs.append(parse_fc_job(entry))
            elif 'msed' == entry_type:
                if previous_job:
                    jobs.append(parse_msed_job(entry, prereq_key=previous_job.key, should_have_lfcs=False))
                else:
                    jobs.append(parse_msed_job(entry, should_have_lfcs=True))
            else:
                raise ValueError(f'Invalid job type {entry_type}')
        except InvalidSubmissionFieldError:
            raise
        except Exception as e:
            raise JobSubmissionError(e, entry_index)
        previous_job = jobs[entry_index]
        entry_index += 1
    return jobs

def parse_mii_lfcs_job(job_data) -> MiiLfcsJob:
    invalid = []
    try:
        # model
        model = job_data['model'].lower()
        if model not in ['old', 'new']:
            invalid.append('model')
        # year
        year = job_data.get('year')
        if year:
            try:
                year = int(year)
                if year < 2011 or year > 2020:
                    invalid.append('year')
            except (ValueError, TypeError) as e:
                invalid.append('year')
        # system id
        system_id = get_system_id_from_mii_lfcs_job(job_data)
        if not system_id:
            invalid.append('mii')
        if invalid:
            raise InvalidSubmissionFieldError(invalid)
        else:
            return MiiLfcsJob(system_id, model, year)
    except KeyError as e:
        raise KeyError(f'Missing parameter {e}')

def get_system_id_from_mii_lfcs_job(job_data) -> str:
    try:
        # explictly declared
        system_id = job_data.get('system_id')
        if system_id:
            return system_id
        # uploaded a mii qr or encrypted bin
        system_id = get_system_id_from_mii_file(job_data)
        if system_id:
            return system_id
    except ValueError as e:
        raise e
    except Exception as e:
        raise ValueError('Could not get LFCS hash from submission') from e

def get_system_id_from_mii_file(job_data) -> str:
    mii_data = base64.b64decode(job_data['mii_data'])
    mii_filename = job_data.get('mii_filename', '')
    mii_mimetype = job_data.get('mii_mimetype')
    # determine uploaded file type and get encrypted mii data
    mii_data_enc = None
    if 112 == len(mii_data) or 'application/octet-stream' == mii_mimetype or mii_filename.lower().endswith('.bin'):
        mii_data_enc = mii_data
    else:
        try:
            decoded = qr_decode(Image.open(io.BytesIO(mii_data)), binary=True)
            if not decoded:
                return
            mii_data_enc = decoded[0].data
        except:
            pass
    # get lfcs from encrypted mii data
    if mii_data_enc:
        nk31 = unhexlify(job_data.get('slot_31_key_n', ''))
        if not nk31:
            nk31 = slot0x31KeyN
        return get_system_id_from_enc_mii(mii_data_enc, nk31)

# Modified from seedminer_launcher3.py by zoogie
# https://github.com/zoogie/seedminer/blob/master/seedminer/seedminer_launcher3.py#L126-L130
def get_system_id_from_enc_mii(mii_data_enc: bytes, nk31: bytes) -> str:
    if 112 != len(mii_data_enc):
        raise ValueError('Incorrect Mii data length')
    if not nk31:
        raise ValueError('slot0x31KeyN not provided')
    # decrypt mii data
    nonce = mii_data_enc[:8] + (b'\x00' * 4)
    cipher = AES.new(nk31, AES.MODE_CCM, nonce)
    mii_data_dec = cipher.decrypt(mii_data_enc[8:0x60])
    # get system id
    system_id = hexlify(mii_data_dec[4:12]).decode('ascii')
    app.logger.debug(f'Got system ID: {system_id}')
    return system_id

def parse_fc_job(job_data) -> FcLfcsJob:
    try:
        # friend code
        friend_code = job_data['friend_code'].replace('-', '')
        if not is_friend_code(friend_code) or is_blacklisted_friend_code(friend_code):
            raise InvalidSubmissionFieldError(['friend_code'])
        else:
            return FcLfcsJob(friend_code)
    except KeyError as e:
        raise KeyError(f'Missing parameter {e}')

def parse_msed_job(job_data, prereq_key=None, should_have_lfcs=True) -> MsedJob:
    invalid = []
    try:
        # id0
        id0 = job_data['id0']
        if not is_id0(id0):
            invalid.append('id0')
        # lfcs
        lfcs = get_lfcs_from_msed_job(job_data, should_have_lfcs)
        if should_have_lfcs and not lfcs:
            invalid.append('lfcs')
        if invalid:
            raise InvalidSubmissionFieldError(invalid)
        else:
            return MsedJob(id0, lfcs=lfcs, prereq_key=prereq_key)
    except KeyError as e:
        raise KeyError(f'Missing parameter {e}')

def get_lfcs_from_msed_job(job_data, should_have_lfcs=True) -> str:
    try:
        # explictly declared
        lfcs = job_data.get('lfcs')
        if lfcs:
            return lfcs
        # uploaded movable_part1.sed
        lfcs = get_lfcs_from_part1_file(job_data)
        if lfcs:
            return lfcs
    except ValueError as e:
        raise e
    except KeyError as e:
        if should_have_lfcs:
            raise e
    except Exception as e:
        raise ValueError('Could not get LFCS from submission') from e

def get_lfcs_from_part1_file(job_data) -> str:
    part1_data = base64.b64decode(job_data['part1_data'])
    lfcs = hexlify(part1_data[:5]).decode('ascii')
    app.logger.debug(f'Got LFCS: {lfcs}')
    return lfcs


def get_request_ip() -> str:
    if request.environ.get('HTTP_X_FORWARDED_FOR') is None:
        return request.environ['REMOTE_ADDR']
    else:
        return request.environ['HTTP_X_FORWARDED_FOR']


class JobSubmissionError(Exception):

    def __init__(self, cause, source):
        self.cause = cause
        self.source = source
        self.message = f'Caught {type(cause).__name__}: {cause}; while parsing job entry {source}'
        super().__init__(self.message)


class InvalidSubmissionFieldError(Exception):

    def __init__(self, invalid):
        self.invalid = invalid
        super().__init__('invalid:' + ','.join(invalid))


# main

if __name__ == '__main__':
    load_dotenv()
    # load AES keys
    try:
        slot0x31KeyN = unhexlify(os.getenv('SLOT_31_KEY_N'))
    except:
        app.logger.warning('Failed loading AES keys!')
    # count previous stats
    mseds_mined = count_mseds_mined()
    lfcses_mined = count_lfcses_mined()
    lfcses_dumped = count_lfcses_dumped()
    app.logger.info('Previous totals:')
    app.logger.info(f'  {mseds_mined} mseds mined')
    app.logger.info(f'  {lfcses_mined} lfcses mined')
    app.logger.info(f'  {lfcses_dumped} lfcses dumped')
    # start web server
    from waitress import serve
    serve(app, host=os.getenv('HOST_ADDR', '127.0.0.1'), port=os.getenv('HOST_PORT', 7799))
