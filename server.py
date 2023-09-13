from flask import Flask, request, render_template, make_response, g
from werkzeug.exceptions import HTTPException
from werkzeug.middleware.proxy_fix import ProxyFix
from functools import wraps
from logging.config import dictConfig

from pyzbar.pyzbar import decode as qr_decode
from PIL import Image

from dotenv import load_dotenv

import base64
import json
import os
import re
import secrets

from jobs import JobManager, MiiJob, Part1Job, read_movable, count_total_mined


# constants
id0_regex = re.compile(r'[a-fA-F0-9]{32}')

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
    response = make_response(render_template(client_filename))
    response.headers.set('Content-Type', 'application/octet-stream')
    response.headers.set('Content-Disposition', 'attachment', filename=client_filename)
    return response


# api routes

@app.route('/api/submit_mii_job', methods=['POST'])
def api_submit_mii_job():
    job = None
    # parse job submission
    submission = request.get_json(silent=True)
    if submission:
        job = parse_mii_job_submission(request.json)
    else:
        job = parse_mii_job_submission(request.form, mii_file=request.files['mii_file'])
    # returns error message if job json is invalid
    if type(job) is str:
        return error(job)
    return submit_generic_job(job, queue=True)

@app.route('/api/submit_part1_job', methods=['POST'])
def api_submit_part1_job():
    job = None
    # parse job submission
    submission = request.get_json(silent=True)
    if submission:
        job = parse_part1_job_submission(request.json)
    else:
        job = parse_part1_job_submission(request.form, part1_file=request.files['part1_file'])
    # returns error message if job json is invalid
    if type(job) is str:
        return error(job)
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
    miner_ip = get_request_ip()
    miner_name = request.args.get('name', miner_ip)
    app.logger.info(f'miner "{miner_name}" ({miner_ip}) requests work')
    job = manager.request_job(miner_name, miner_ip)
    if job:
        app.logger.info('job assigned: \t' + job.id0)
        return success(dict(job))
    else:
        return success()

@app.route('/api/release_job/<id0>')
def api_release_job(id0):
    if not is_id0(id0):
        return error('Invalid ID0')
    manager.release_job(id0)
    app.logger.info('job released: \t' + id0)
    return success()

@app.route('/api/check_job_status/<id0>')
def api_check_job_status(id0):
    if not is_id0(id0):
        return error('Invalid ID0')
    status = manager.check_job_status(id0)
    return success({'status': status})

@app.route('/api/update_job/<id0>')
def api_update_job(id0):
    if not is_id0(id0):
        return error('Invalid ID0')
    miner_ip = get_request_ip()
    app.logger.info(f'{miner_ip} is still mining')
    if manager.update_job(id0, miner_ip=miner_ip):
        return success()
    else:
        return success({'status': 'canceled'})

@app.route('/api/cancel_job/<id0>')
def api_cancel_job(id0):
    trim_canceled_jobs()
    if not is_id0(id0):
        return error('Invalid ID0')
    manager.cancel_job(id0)
    app.logger.info('job canceled: \t' + id0)
    return success()

@app.route('/api/reset_job/<id0>')
def api_reset_job(id0):
    if not is_id0(id0):
        return error('Invalid ID0')
    manager.reset_job(id0)
    app.logger.info('job reset: \t' + id0)
    return success()

@app.route('/api/complete_job/<id0>', methods=['POST'])
def api_complete_job(id0):
    global total_mined
    if not is_id0(id0):
        return error('Invalid ID0')
    movable = base64.b64decode(request.json['movable'])
    manager.complete_job(id0, movable)
    app.logger.info('job completed: \t' + id0)
    total_mined += 1
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


# error handler

@app.errorhandler(Exception)
def handle_exception(e):
    # pass through HTTP errors
    if isinstance(e, HTTPException):
        return e
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
        status = manager.check_job_status(job.id0)
        # delete existing job if it is canceled
        if 'canceled' == status:
            app.logger.info('deleting old job: \t' + job.id0)
            manager.delete_job(job.id0)
            status = None
        if status:
            return error('Duplicate job')
    except: # job does not exist
        pass
    # submit and queue
    manager.submit_job(job)
    if queue:
        manager.queue_job(job.id0)
    app.logger.info(f'{job.type} job submitted: \t{job.id0}')
    return success({'id0': job.id0})

def release_dead_jobs():
    released = manager.release_dead_jobs()
    if released:
        app.logger.info('jobs released:')
        for id0 in released:
            app.logger.info(f'\t\t{id0}')

def trim_canceled_jobs():
    deleted = manager.trim_canceled_jobs()
    if deleted:
        app.logger.info('jobs deleted:')
        for id0 in deleted:
            app.logger.info(f'\t\t{id0}')


# helpers

def is_id0(value):
    return bool(id0_regex.fullmatch(value))

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
        mii_data = submission.get('mii_data')
        if mii_file:
            mii_data = process_mii_file(mii_file)
        if not mii_data:
            invalid.append('mii')
        if invalid:
            return 'invalid:' + ','.join(invalid)
        else:
            return MiiJob(id0, model, year, mii_data)
    except KeyError as e:
        raise KeyError(f'Missing parameter {e}')

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
    # base64 encode
    if raw_data and len(raw_data) == 112:
        return str(base64.b64encode(raw_data), 'utf-8')

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
