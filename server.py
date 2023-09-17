from flask import Flask, request, render_template, make_response, g
from werkzeug.exceptions import HTTPException
from werkzeug.middleware.proxy_fix import ProxyFix
from functools import wraps
from logging.config import dictConfig

from pyzbar.pyzbar import decode as qr_decode
from PIL import Image

#from Cryptodome.Cipher import AES
from Crypto.Cipher import AES
from binascii import hexlify

from dotenv import load_dotenv

import base64
import hashlib
import json
import os
import re
import secrets
import struct

from jobs import JobManager, MiiJob, FCJob, Part1Job, read_movable, count_total_mined


# constants
id0_regex = re.compile(r'(?![0-9a-fA-F]{4}(01|00)[0-9a-fA-F]{18}00[0-9a-fA-F]{6})[0-9a-fA-F]{32}')
mii_final_regex = re.compile(r'[a-fA-F0-9]{16}')
version_split_regex = re.compile(r'[.+-]')

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

# mining client version
mining_client_version = '1.0.0-fix1'

# total movables mined
total_mined = 0


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

@app.route('/mii')
def page_mii():
    return render_template('pages/mii.html')

@app.route('/fc')
def page_fc():
    return render_template('pages/fc.html')

@app.route('/part1')
def page_part1():
    return render_template('pages/part1.html')

@app.route('/volunteer')
def page_volunteer():
    return render_template('pages/volunteer.html')

@app.route('/admin')
@login_required
def page_admin():
    return render_template('pages/admin.html')

@app.route('/js/<path:filename>')
def serve_js(filename):
    response = make_response(render_template('js/' + filename))
    response.headers.set('Content-Type', 'text/javascript')
    return response

@app.route('/get_mining_client')
def get_mining_client():
    client_filename = 'mining_client.py'
    response = make_response(render_template(client_filename, client_version=mining_client_version))
    response.headers.set('Content-Type', 'application/octet-stream')
    response.headers.set('Content-Disposition', 'attachment', filename=client_filename)
    return response


# api routes

@app.route('/api/submit_mii_job', methods=['POST'])
def api_submit_mii_job():
    job = None
    part1_job = None
    # parse job submission
    submission = request.get_json(silent=True)
    if submission:
        job = parse_mii_job_submission(request.json)
        part1_job = parse_part1_job_submission(request.json)
    else:
        job = parse_mii_job_submission(request.form, mii_file=request.files['mii_file'])
        part1_job = parse_part1_job_submission(request.form)
    # returns error message if job json is invalid
    if type(job) is str:
        return error(job)
    if type(part1_job) is str:
        return error(part1_job)
    part1_job.prerequisite = job.key
    part1_res = submit_generic_job(part1_job, no_response=True)
    if not part1_res[0]:
        return error(part1_res[1])
    res = submit_generic_job(job, queue=True, no_response=True)
    if not res[0]:
        manager.fulfill_job(job.key)
    return success({
        'mii' : res[1].key if res[0] else '',
        'id0' : part1_res[1].key
    })

@app.route('/api/submit_fc_job', methods=['POST'])
def api_submit_fc_job():
    job = None
    part1_job = None
    # parse job submission
    submission = request.get_json(silent=True)
    if submission:
        job = parse_fc_job_submission(request.json)
        part1_job = parse_part1_job_submission(request.json)
    else:
        job = parse_fc_job_submission(request.form)
        part1_job = parse_part1_job_submission(request.form)
    # returns error message if job json is invalid
    if type(job) is str:
        return error(job)
    if type(part1_job) is str:
        return error(part1_job)
    part1_job.prerequisite = job.key
    part1_res = submit_generic_job(part1_job, no_response=True)
    if not part1_res[0]:
        return error(part1_res[1])
    res = submit_generic_job(job, queue=True, no_response=True)
    return success({
        'fc' : res[1].key if res[0] else '',
        'id0' : part1_res[1].key
    })

@app.route('/api/submit_part1_job', methods=['POST'])
def api_submit_part1_job():
    job = None
    # parse job submission
    submission = request.get_json(silent=True)
    if submission:
        job = parse_part1_job_submission(request.json)
    else:
        job = parse_part1_job_submission(request.form, part1_file=request.files.get('part1_file'))
    # returns error message if job json is invalid
    if type(job) is str:
        return error(job)
    res = submit_generic_job(job, queue=job.has_part1(), no_response=True)
    if res[0]:
        return success({'key': res[1].key})
    elif manager.job_exists(job.key) and manager.check_job_status(job.key) == 'need_part1':
        if job.has_part1():
            manager.add_part1(job.key, job.part1)
            manager.queue_job(job.key)
            return success({'key': job.key})
        else:
            return error('need_part1')
    else:
        return submit_generic_job(job, queue=job.has_part1())

@app.route('/api/add_part1/<id0>', methods=['POST'])
def api_add_part1(id0):
    if not is_id0(id0):
        return error('Invalid ID0')
    submission = request.get_json(silent=True)
    if submission:
        part1_data = parse_part1_upload(request.json)
    else:
        part1_data = parse_part1_upload(request.form, part1_file=request.files['part1_file'])
    manager.add_part1(id0, part1_data)
    manager.queue_job(id0)
    return success()

@app.route('/api/request_job')
def api_request_job():
    release_dead_jobs()
    # miner info
    miner_ip = get_request_ip()
    miner_name = request.args.get('name', miner_ip)
    accepted_types = request.args.get('types')
    app.logger.info(f'{log_prefix()} {miner_name} requests work')
    # reject old versions
    try:
        miner_version = request.args['version']
        if compare_versions(miner_version, mining_client_version) < 0:
            return error('Outdated client version')
    except Exception as e:
        app.logger.exception(e)
        return error('Unknown client version')
    # check for and assign jobs
    job = manager.request_job(miner_name, miner_ip, accepted_types)
    if job:
        app.logger.info(f'{log_prefix(job.key)} assigned to {miner_name}')
        return success(dict(job))
    else:
        return success()

@app.route('/api/release_job/<key>')
def api_release_job(key):
    if not is_job_key(key):
        return error('Invalid Job Key')
    manager.release_job(key)
    app.logger.info(f'{log_prefix(key)} released')
    return success()

@app.route('/api/check_job_status/<key>')
def api_check_job_status(key):
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
def api_update_job(key):
    if not is_job_key(key):
        return error('Invalid Job Key')
    app.logger.info(f'{log_prefix(key)} still mining')
    if manager.update_job(key, miner_ip=get_request_ip()):
        return success()
    else:
        return success({'status': 'canceled'})

@app.route('/api/cancel_job/<key>')
def api_cancel_job(key):
    trim_canceled_jobs()
    if not is_job_key(key):
        return error('Invalid Job Key')
    manager.cancel_job(key)
    app.logger.info(f'{log_prefix(key)} canceled')
    return success()

@app.route('/api/reset_job/<key>')
def api_reset_job(key):
    if not is_job_key(key):
        return error('Invalid Job Key')
    manager.reset_job(key)
    app.logger.info(f'{log_prefix(key)} reset')
    return success()

@app.route('/api/complete_job/<key>', methods=['POST'])
def api_complete_job(key):
    global total_mined
    if not is_job_key(key):
        return error('Invalid Job Key')
    result = base64.b64decode(request.json['result'])
    manager.complete_job(key, result)
    app.logger.info(f'{log_prefix(key)} completed')
    total_mined += 1
    return success()

@app.route('/api/fail_job/<key>', methods=['POST'])
def api_fail_job(key):
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
        'miners': manager.count_miners(active_only=True),
        'totalMined': total_mined
    })

@app.route('/api/admin/list_jobs')
@login_required
def api_admin_list_jobs():
    with manager.lock:
        return success({
            'jobs': [dict(j) for j in manager.list_jobs()],
            'queue': list(manager.wait_queue)
        })

@app.route('/api/admin/list_miners')
@login_required
def api_admin_list_miners():
    with manager.lock:
        return success({
            'miners': [dict(m) for m in manager.list_miners()]
        })


# response templates

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

def log_prefix(key=None):
    prefix = '(' + get_request_ip() + ')'
    if key:
        prefix += f' {key}'
    return prefix

# error handler

@app.errorhandler(Exception)
def handle_exception(e):
    # pass through HTTP errors
    if isinstance(e, HTTPException):
        return e
    app.logger.error(f'{log_prefix()} caught exception')
    app.logger.exception(e)
    return error(f'{type(e).__name__}: {e}', code=500)


# download movable

@app.route('/download_movable/<id0>')
def download_movable(id0):
    if not is_id0(id0):
        return error('Invalid ID0')
    movable = read_movable(id0)
    if not movable:
        return error('Movable not found', 404)
    response = make_response(movable)
    response.headers.set('Content-Type', 'application/octet-stream')
    response.headers.set('Content-Disposition', 'attachment', filename=f'movable.sed')
    return response


# manager action wrappers

def submit_generic_job(job, queue=False, no_response=False):
    # check for existing job
    status = None
    try:
        status = manager.check_job_status(job.key)
        # delete existing job if it is canceled
        if 'canceled' == status:
            app.logger.info(f'{log_prefix(job.key)} overwritten')
            manager.delete_job(job.key)
            status = None
        if status:
            return (False, 'Duplicate job') if no_response else error('Duplicate job')
    except: # job does not exist
        pass
    # submit and queue
    manager.submit_job(job)
    if queue:
        manager.queue_job(job.key)
    app.logger.info(f'{log_prefix(job.key)} submitted ({job.type})')
    return (True, job) if no_response else success({'key': job.key})

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


# helpers

def is_job_key(value):
    return is_id0 or is_mii_final or is_friend_code

def is_id0(value):
    return bool(id0_regex.fullmatch(value))

def is_mii_final(value):
    return bool(mii_final_regex.fullmatch(value))

# Modified from https://github.com/nh-server/Kurisu/blob/main/cogs/friendcode.py#L28
def is_friend_code(value):
    try:
        fc = int(value)
    except ValueError:
        return False
    if fc > 0x7FFFFFFFFF:
        return False
    principal_id = fc & 0xFFFFFFFF
    checksum = (fc & 0xFF00000000) >> 32
    return hashlib.sha1(struct.pack('<L', principal_id)).digest()[0] >> 1 == checksum

# Modified from https://stackoverflow.com/a/28568003
def parse_version_string(version_str, point_max_len=10):
   filled = []
   for point in version_split_regex.split(version_str):
      filled.append(point.zfill(point_max_len))
   return tuple(filled)

def compare_versions(version_a, version_b):
    if len(version_a) != len(version_b):
        raise ValueError('Lengths do not match')
    return compare(version_a, version_b)

# removed in Python 3 lol
def compare(a, b):
    return (a > b) - (a < b) 

def parse_mii_job_submission(submission, mii_file=None):
    invalid = []
    try:
        # id0
        id0 = submission['id0']
        if not is_id0(id0):
            invalid.append('id0')
        # model
        model = submission['model'].lower()
        if model not in ['old', 'new']:
            invalid.append('model')
        # year
        year = None
        if submission['year']:
            try:
                year = int(submission['year'])
                if year < 2011 or year > 2020:
                    invalid.append('year')
            except (ValueError, TypeError) as e:
                invalid.append('year')
        # mii data
        mii_final = submission.get('mii_final')
        if mii_file:
            mii_final = process_mii_file(mii_file)
        if not mii_final:
            invalid.append('mii')
        if invalid:
            return 'invalid:' + ','.join(invalid)
        else:
            return MiiJob(mii_final, model, year, mii_final)
    except KeyError as e:
        raise KeyError(f'Missing parameter "{e}"')

def parse_fc_job_submission(submission):
    invalid = []
    try:
        # id0
        id0 = submission['id0']
        if not is_id0(id0):
            invalid.append('id0')
        # friend code
        friend_code = submission.get('friend_code').replace('-', '')
        if friend_code and not is_friend_code(friend_code):
            invalid.append('friend_code')
        if invalid:
            return 'invalid:' + ','.join(invalid)
        else:
            return FCJob(friend_code)
    except KeyError as e:
        raise KeyError(f'Missing parameter "{e}"')

def parse_part1_job_submission(submission, part1_file=None):
    invalid = []
    try:
        # id0
        id0 = submission['id0']
        if not is_id0(id0):
            invalid.append('id0')
        # part1 data
        part1_data = parse_part1_upload(submission, part1_file)
        if invalid:
            return 'invalid:' + ','.join(invalid)
        else:
            return Part1Job(id0, part1=part1_data)
    except KeyError as e:
        raise KeyError(f'Missing parameter "{e}"')

def parse_part1_upload(submission, part1_file=None):
    try:
        part1_data = submission.get('part1_data')
        if part1_file:
            part1_data = process_part1_file(part1_file)
        return part1_data
    except:
        raise ValueError('Could not parse part1 data')

def process_mii_file(mii_file):
    filename = mii_file.filename.lower()
    raw_data = None
    # determine upload type
    if mii_file.mimetype == 'application/octet-stream' or filename.endswith('.bin'):
        raw_data = mii_file.read()
    else:
        try:
            decoded = qr_decode(Image.open(mii_file), binary=True)
            if not decoded:
                return
            raw_data = decoded[0].data
        except:
            pass
    if raw_data and len(raw_data) == 112:
        # from seedminer_launcher3.py by zoogie
        # https://github.com/zoogie/seedminer/blob/master/seedminer/seedminer_launcher3.py#L126-L130
        nonce = raw_data[:8] + b"\x00" * 4
        nk31 = 0x59FC817E6446EA6190347B20E9BDCE52
        cipher = AES.new(nk31.to_bytes(16, 'big'), AES.MODE_CCM, nonce)
        dec = cipher.decrypt(raw_data[8:0x60])
        nonce = nonce[:8]
        final = dec[:12] + nonce + dec[12:]
        app.logger.info(hexlify(final[4:4 + 8]).decode('ascii'))
        return hexlify(final[4:4 + 8]).decode('ascii')

def process_part1_file(part1_file):
    raw_data = part1_file.read()
    # base64 encode
    if raw_data and len(raw_data) > 0: # better size checking once I'm sure, 0x1000 bytes?
        return str(base64.b64encode(raw_data), 'utf-8')

def get_request_ip():
    if request.environ.get('HTTP_X_FORWARDED_FOR') is None:
        return request.environ['REMOTE_ADDR']
    else:
        return request.environ['HTTP_X_FORWARDED_FOR']


# main

if __name__ == '__main__':
    load_dotenv()
    total_mined = count_total_mined()
    app.logger.info(f'mined {total_mined} movables previously')
    from waitress import serve
    serve(app, host=os.getenv('HOST_ADDR', '127.0.0.1'), port=os.getenv('HOST_PORT', 7799))
