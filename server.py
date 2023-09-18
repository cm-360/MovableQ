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

from jobs import JobManager, MiiJob, FCJob, Part1Job, read_movable, count_mseds_mined


# constants
id0_regex = re.compile(r'(?![0-9a-fA-F]{4}(01|00)[0-9a-fA-F]{18}00[0-9a-fA-F]{6})[0-9a-fA-F]{32}')
lfcs_hash_regex = re.compile(r'[a-fA-F0-9]{16}')
version_split_regex = re.compile(r'[.+-]')

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

# mining client info
mining_client_filename = 'mining_client.py'
mining_client_version = '1.0.0-fix1'

# total movables mined
mseds_mined = 0


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
    response = make_response(render_template(mining_client_filename, client_version=mining_client_version))
    response.headers.set('Content-Type', 'application/octet-stream')
    response.headers.set('Content-Disposition', 'attachment', filename=mining_client_filename)
    return response


# api routes

@app.route('/api/submit_job_chain', methods=['POST'])
def api_submit_job_chain():
    submission = request.get_json(silent=True)
    if not submission:
        return error('Missing request JSON')
    chain = parse_job_chain_submission(submission)
    manager.submit_job_chain(chain)
    return success()

@app.route('/api/submit_mii_job', methods=['POST'])
def api_submit_mii_job():
    main_job = None
    part1_job = None
    # parse job submission
    submission = request.get_json(silent=True)
    if submission:
        main_job  = parse_mii_job_submission(request.json)
        part1_job = parse_part1_job_submission(request.json)
    else:
        main_job  = parse_mii_job_submission(request.form, mii_file=request.files['mii_file'])
        part1_job = parse_part1_job_submission(request.form)
    # returns error message if job json is invalid
    if type(main_job) is str:
        return error(mii_job)
    if type(part1_job) is str:
        return error(part1_job)
    part1_job.prerequisite = main_job.key
    part1_res = submit_generic_job(part1_job)
    if not part1_res[0]:
        return error(part1_res[1])
    res = submit_generic_job(main_job, queue=True)
    if not res[0]:
        manager.fulfill_job(main_job.key)
    return success({
        'mii' : res[1].key if res[0] else '',
        'id0' : part1_res[1].key
    })

@app.route('/api/submit_fc_job', methods=['POST'])
def api_submit_fc_job():
    main_job = None
    part1_job = None
    # parse job submission
    submission = request.get_json(silent=True)
    if submission:
        main_job  = parse_fc_job_submission(request.json)
        part1_job = parse_part1_job_submission(request.json)
    else:
        main_job  = parse_fc_job_submission(request.form)
        part1_job = parse_part1_job_submission(request.form)
    # returns error message if job json is invalid
    if type(main_job) is str:
        return error(main_job)
    if type(part1_job) is str:
        return error(part1_job)
    part1_job.prerequisite = job.key
    part1_res = submit_generic_job(part1_job)
    if not part1_res[0]:
        return error(part1_res[1])
    res = submit_generic_job(job, queue=True)
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
    res = submit_generic_job(job, queue=job.has_part1())
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
        return error(res[1])

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
        miner_version = request.args.get('version')
        if not miner_version:
            return error('Client version not provided')
        if compare_versions(miner_version, mining_client_version) < 0:
            return error(f'Outdated client version, {miner_version} < {mining_client_version}')
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
    global mseds_mined
    if not is_job_key(key):
        return error('Invalid Job Key')
    result = base64.b64decode(request.json['result'])
    if validate_job_result(key, result):
        manager.complete_job(key, result)
        app.logger.info(f'{log_prefix(key)} completed')
        mseds_mined += 1
    else:
        app.logger.info(f'{log_prefix(key)} uploaded faulty result')
        manager.fail_job(key, 'miner uploaded faulty result') # probably shouldn't fail?
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
        'totalMined': mseds_mined
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

def submit_generic_job(job, queue=False):
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
            return (False, 'Duplicate job')
    except: # job does not exist
        pass
    # submit and queue
    manager.submit_job(job)
    if queue:
        manager.queue_job(job.key)
    app.logger.info(f'{log_prefix(job.key)} submitted ({job.type})')
    return (True, job)

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
    return is_id0 or is_lfcs_hash or is_friend_code

def is_id0(value):
    return bool(id0_regex.fullmatch(value))

def is_lfcs_hash(value):
    return bool(lfcs_hash_regex.fullmatch(value))

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

def validate_job_result(key, result):
    if len(key) == 16: # mii -> lfcs
        if len(result) < 5:
            return False
        if b"\0\0\0\0" in result[:4]:
            return False
        #if result[4:5] != b"\x00" && result[4:5] != b"\x02":
        #    return False
        return True

    elif len(key) == 32: # part1 -> mkey
        if len(result) != 16:
            return False
        return True

    else:
        return False

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

def parse_job_chain(chain_data):
    jobs = []
    for entry in chain_data:
        entry_type = entry['type']
        if 'mii' == entry_type:
            jobs.append(parse_mii_job(entry))
        elif 'fc' == entry_type:
            jobs.append(parse_fc_job(entry))
        elif 'part1' == entry_type:
            jobs.append(parse_part1_job(entry))
        else:
            raise ValueError(f'Invalid job type "{entry_type}"')
    return jobs

def parse_mii_job(job_data):
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
        # lfcs hash
        lfcs_hash = get_lfcs_hash_from_mii_job(job_data)
        if not lfcs_hash:
            invalid.append('lfcs_hash')
        if invalid:
            raise ValueError('invalid:' + ','.join(invalid))
        else:
            return MiiJob(lfcs_hash, model, year)
    except KeyError as e:
        raise KeyError(f'Missing parameter "{e}"')

def get_lfcs_hash_from_mii_job(job_data):
    try:
        # explictly declared
        lfcs_hash = job_data.get('lfcs_hash')
        if lfcs_hash:
            return lfcs_hash
        # uploaded a mii qr or encrypted bin
        lfcs_hash = get_lfcs_hash_from_mii_file(job_data)
        if lfcs_hash:
            return lfcs_hash
    except ValueError as e:
        raise e
    except Exception as e:
        raise ValueError('Could not get LFCS hash from submission') from e

def get_lfcs_hash_from_mii_file(job_data):
    mii_data = base64.b64decode(job_data['mii_data'])
    mii_filename = job_data.get('mii_filename', '')
    mii_mimetype = job_data.get('mii_mimetype')
    # determine uploaded file type and get encrypted mii data
    mii_data_enc = None
    if 'application/octet-stream' == mii_mimetype or mii_filename.lower().endswith('.bin'):
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
        return get_lfcs_hash_from_enc_mii(mii_data_enc)

# Modified from seedminer_launcher3.py by zoogie
# https://github.com/zoogie/seedminer/blob/master/seedminer/seedminer_launcher3.py#L126-L130
def get_lfcs_hash_from_enc_mii(mii_data_enc):
    if 112 != len(mii_data_enc):
        raise ValueError('Incorrect Mii data length')
    # decrypt mii data
    nonce = mii_data_enc[:8] + (b'\x00' * 4)
    cipher = AES.new(slot0x31KeyN.to_bytes(16, 'big'), AES.MODE_CCM, nonce)
    mii_data_dec = cipher.decrypt(mii_data_enc[8:0x60])
    # get lfcs hash
    lfcs_hash = hexlify(mii_data_dec[4:12]).decode('ascii')
    app.logger.debug(f'Got LFCS hash: {lfcs_hash}')
    return lfcs_hash

def parse_fc_job(job_data):
    try:
        # friend code
        friend_code = job_data['friend_code'].replace('-', '')
        if not is_friend_code(friend_code):
            raise ValueError('invalid:friend_code')
        else:
            return FCJob(friend_code)
    except KeyError as e:
        raise KeyError(f'Missing parameter "{e}"')

def parse_part1_job(job_data):
    invalid = []
    try:
        # id0
        id0 = job_data['id0']
        if not is_id0(id0):
            invalid.append('id0')
        # lfcs
        lfcs = get_lfcs_from_part1_job(job_data)
        if not lfcs:
            invalid.append('part1')
        if invalid:
            raise ValueError('invalid:' + ','.join(invalid))
        else:
            return Part1Job(id0, part1=lfcs)
    except KeyError as e:
        raise KeyError(f'Missing parameter "{e}"')

def get_lfcs_from_part1_job(job_data):
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
    except Exception as e:
        raise ValueError('Could not get LFCS from submission') from e

def get_lfcs_from_part1_file(job_data):
    part1_data = base64.b64decode(job_data['part1_data'])
    lfcs = hexlify(part1_data[:5]).decode('ascii')
    app.logger.debug(f'Got LFCS: {lfcs}')
    return lfcs


def get_request_ip():
    if request.environ.get('HTTP_X_FORWARDED_FOR') is None:
        return request.environ['REMOTE_ADDR']
    else:
        return request.environ['HTTP_X_FORWARDED_FOR']


# main

if __name__ == '__main__':
    load_dotenv()
    mseds_mined = count_mseds_mined()
    app.logger.info(f'mined {mseds_mined} movables previously')
    from waitress import serve
    serve(app, host=os.getenv('HOST_ADDR', '127.0.0.1'), port=os.getenv('HOST_PORT', 7799))
