from flask import Flask, request, render_template, make_response, g
from werkzeug.exceptions import HTTPException
from werkzeug.middleware.proxy_fix import ProxyFix
from functools import wraps
from logging.config import dictConfig

from pyzbar.pyzbar import decode as qr_decode
from PIL import Image

#from Cryptodome.Cipher import AES
from Crypto.Cipher import AES
from binascii import hexlify, unhexlify

from dotenv import load_dotenv

import base64
import json
import os
import re

from jobs import JobManager, Job, MiiJob, FCJob, Part1Job, read_movable, count_mseds_mined, count_lfcses_mined, count_lfcses_dumped
from validators import is_job_key, is_id0, is_system_id, is_friend_code, validate_job_result, enforce_client_version


# AES keys
slot0x31KeyN = 0x59FC817E6446EA6190347B20E9BDCE52

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
        'version': '1.0.0-fix1',
        'allowed': {'mii', 'part1'}
    },
    'friendbot': {
        'version': '1.0.0',
        'allowed': {'fc'}
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

@app.route('/submit')
def page_submit():
    return render_template('pages/submit.html')

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

@app.route('/get_mining_client')
def get_mining_client():
    client_version = f'miiner-{client_types["miiner"]["version"]}'
    response = make_response(render_template(mining_client_filename, client_version=client_version))
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
    # parse and submit chain
    chain = parse_job_chain(submission)
    manager.submit_job_chain(chain)
    # queue jobs with no prerequisites
    first_job = chain[0]
    if 'ready' == first_job.state:
        manager.queue_job(first_job.key)
    # return job keys to submitter
    chain_keys = [j.key for j in chain]
    app.logger.info(f'{log_prefix(",".join(chain_keys))} submitted')
    return success(chain_keys)

@app.route('/api/submit_mii_job', methods=['POST'])
def api_submit_mii_job():
    return error('Not implemented')

@app.route('/api/submit_fc_job', methods=['POST'])
def api_submit_fc_job():
    return error('Not implemented')

@app.route('/api/submit_part1_job', methods=['POST'])
def api_submit_part1_job():
    return error('Not implemented')

@app.route('/api/request_job')
def api_request_job():
    release_dead_jobs()
    # worker info
    worker_ip = get_request_ip()
    worker_name = request.args.get('name', worker_ip)
    app.logger.info(f'{log_prefix()} {worker_name} requests work')
    # restrict clients
    client_version = request.args.get('version')
    requested_types = request.args.get('types')
    if requested_types:
        requested_types = set(requested_types.split(','))
    allowed_types = enforce_client_version(client_types, client_version, requested_types)
    # check for and assign jobs
    job = manager.request_job(allowed_types, worker_name, worker_ip)
    if job:
        app.logger.info(f'{log_prefix(job.key)} assigned to {worker_name}')
        return success(dict(job))
    else:
        return success()

@app.route('/api/release_job/<key>')
def api_release_job(key: str):
    if not is_job_key(key):
        return error('Invalid Job Key')
    manager.release_job(key)
    app.logger.info(f'{log_prefix(key)} released')
    return success()

@app.route('/api/check_job_status/<key>')
def api_check_job_status(key: str):
    if not is_job_key(key):
        return error('Invalid Job Key')
    status = manager.check_job_status(key)
    if request.args.get('include_stats') and not 'done' == status:
        return success({
            'status': status,
            'mining_stats': manager.get_mining_stats(key)
        })
    else:
        return success({'status': status})

@app.route('/api/update_job/<key>')
def api_update_job(key: str):
    if not is_job_key(key):
        return error('Invalid Job Key')
    app.logger.info(f'{log_prefix(key)} still mining')
    if manager.update_job(key, worker_ip=get_request_ip()):
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
def api_complete_job(key: str):
    global mseds_mined
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
        else:
            raise ValueError(f'Unknown result format {result_format}')
    except KeyError as e:
        raise KeyError(f'Missing parameter {e}')
    # validate result
    job_type = manager.get_job(key).type
    if not validate_job_result(job_type, result, key):
        app.logger.warning(f'{log_prefix(key)} got faulty result')
        manager.release_job(key)
        return error('Faulty result')
    # complete job
    manager.complete_job(key, result)
    app.logger.info(f'{log_prefix(key)} completed')
    # update counter
    if 'part1' == job_type:
        mseds_mined += 1
    elif 'mii' == job_type:
        lfcses_mined += 1
    elif 'fc' == job_type:
        lfcses_dumped += 1
    return success()

@app.route('/api/fail_job/<key>', methods=['POST'])
def api_fail_job(key: str):
    if not is_job_key(key):
        return error('Invalid Job Key')
    manager.fail_job(key, request.json.get('note'))
    app.logger.info(f'{log_prefix(key)} failed')
    return success()

@app.route('/api/check_network_stats')
def api_check_network_stats():
    return success({
        'waiting': manager.count_jobs('waiting'),
        'working': manager.count_jobs('working'),
        # TODO count miners separately
        'workers': manager.count_workers(active_only=True),
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

def log_prefix(key=None) -> str:
    prefix = '(' + get_request_ip() + ')'
    if key:
        prefix += f' {key}'
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
            if 'mii' == entry_type:
                jobs.append(parse_mii_job(entry))
            elif 'fc' == entry_type:
                jobs.append(parse_fc_job(entry))
            elif 'part1' == entry_type:
                jobs.append(parse_part1_job(entry, prereq_key=previous_job.key, should_have_lfcs=False))
            else:
                raise ValueError(f'Invalid job type {entry_type}')
        except Exception as e:
            raise JobSubmissionError(e, entry_index)
        previous_job = jobs[entry_index]
        entry_index += 1
    return jobs

def parse_mii_job(job_data) -> MiiJob:
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
        system_id = get_system_id_from_mii_job(job_data)
        if not system_id:
            invalid.append('system_id')
        if invalid:
            raise InvalidSubmissionFieldError(invalid)
        else:
            return MiiJob(system_id, model, year)
    except KeyError as e:
        raise KeyError(f'Missing parameter {e}')

def get_system_id_from_mii_job(job_data) -> str:
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
            decoded = qr_decode(Image.open(mii_data), binary=True)
            if not decoded:
                return
            mii_data_enc = decoded[0].data
        except:
            pass
    # get lfcs from encrypted mii data
    if mii_data_enc:
        return get_system_id_from_enc_mii(mii_data_enc)

# Modified from seedminer_launcher3.py by zoogie
# https://github.com/zoogie/seedminer/blob/master/seedminer/seedminer_launcher3.py#L126-L130
def get_system_id_from_enc_mii(mii_data_enc: bytes) -> str:
    if 112 != len(mii_data_enc):
        raise ValueError('Incorrect Mii data length')
    # decrypt mii data
    nonce = mii_data_enc[:8] + (b'\x00' * 4)
    cipher = AES.new(slot0x31KeyN.to_bytes(16, 'big'), AES.MODE_CCM, nonce)
    mii_data_dec = cipher.decrypt(mii_data_enc[8:0x60])
    # get system id
    system_id = hexlify(mii_data_dec[4:12]).decode('ascii')
    app.logger.debug(f'Got system ID: {system_id}')
    return system_id

def parse_fc_job(job_data) -> FCJob:
    try:
        # friend code
        friend_code = job_data['friend_code'].replace('-', '')
        if not is_friend_code(friend_code):
            raise InvalidSubmissionFieldError(['friend_code'])
        else:
            return FCJob(friend_code)
    except KeyError as e:
        raise KeyError(f'Missing parameter {e}')

def parse_part1_job(job_data, prereq_key=None, should_have_lfcs=True) -> Part1Job:
    invalid = []
    try:
        # id0
        id0 = job_data['id0']
        if not is_id0(id0):
            invalid.append('id0')
        # lfcs
        lfcs = get_lfcs_from_part1_job(job_data, should_have_lfcs)
        if should_have_lfcs and not lfcs:
            invalid.append('lfcs')
        if invalid:
            raise InvalidSubmissionFieldError(invalid)
        else:
            return Part1Job(id0, lfcs=lfcs, prereq_key=prereq_key)
    except KeyError as e:
        raise KeyError(f'Missing parameter {e}')

def get_lfcs_from_part1_job(job_data, should_have_lfcs=True) -> str:
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
    # count previous stats
    mseds_mined = count_mseds_mined()
    lfcses_mined = count_lfcses_mined()
    lfcses_dumped = count_lfcses_dumped()
    app.logger.info('Previous totals:')
    app.logger.info(f'  {mseds_mined} mseds mined')
    app.logger.info(f'  {lfcses_mined} lfcses mined')
    app.logger.info(f'  {lfcses_dumped} dumped')
    # start web server
    from waitress import serve
    serve(app, host=os.getenv('HOST_ADDR', '127.0.0.1'), port=os.getenv('HOST_PORT', 7799))
