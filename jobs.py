from transitions import Machine

from collections import deque
from datetime import datetime, timedelta, timezone
import base64
import json
import os
from threading import RLock
from binascii import hexlify

from validators import is_id0, is_system_id, is_friend_code, get_key_type

import requests
from requests_html import HTMLSession


fc_lfcses_path = os.getenv('FC_LFCSES_PATH', './lfcses/fc')
sid_lfcses_path = os.getenv('SID_LFCSES_PATH', './lfcses/sid')
mseds_path = os.getenv('MSEDS_PATH', './mseds')
bfm_site_base = os.getenv('BFM_SITE_BASE', 'https://seedminer.hacks.guide')
bfm_site_endpoint = os.getenv('BFM_SITE_ENDPOINT', '')

job_lifetime = timedelta(minutes=5)
worker_lifetime = timedelta(minutes=10)

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
# mii mining boundary from ocl_brute.c by zoogie
# https://github.com/zoogie/bfCL/blob/master/ocl_brute.c#L505-L506
lfcs_min_old = 0
lfcs_max_old = 0x0B000000
lfcs_min_new = 0
lfcs_max_new = 0x05000000

class JobManager():

    def __init__(self):
        self.jobs = {}
        self.wait_queue = deque()
        self.workers = {}
        self.lock = RLock()

    def get_job(self, key):
        with self.lock:
            return self.jobs[key]

    # adds a job to the current job list, raises a ValueError if it exists already
    def submit_job(self, job, overwrite_canceled=False):
        with self.lock:
            if self.job_exists(job.key):
                if overwrite_canceled and self.jobs[job.key].is_canceled():
                    self.delete_job(job.key)
                else:
                    raise ValueError(f'Duplicate job: {job.key}')
            self.jobs[job.key] = job

    def submit_job_chain(self, chain, overwrite_canceled=False):
        with self.lock:
            end_job = chain[-1]
            if end_job.is_already_done():
                # if the end (target) job is already done, skip the whole chain
                return
            to_delete = []
            # loop twice so we submit no jobs if any are duplicates
            for job in chain:
                if not self.job_exists(job.key):
                    continue
                if overwrite_canceled and self.jobs[job.key].is_canceled():
                    to_delete.append(job.key)
                else:
                    raise ValueError(f'Duplicate job: {job.key}')
            for key in to_delete:
                self.delete_job(key)
            for job in chain:
                self.jobs[job.key] = job

    # set job status to canceled, KeyError if it does not exist
    def cancel_job(self, key):
        with self.lock:
            job = self.jobs[key]
            job.to_canceled()
            self._unqueue_job(key)

    # reset a canceled job
    def reset_job(self, key):
        with self.lock:
            job = self.jobs[key]
            job.reset()
            job.prepare()
            if job.is_ready():
                self.queue_job(key)

    # delete job from the current job list if exists
    def delete_job(self, key):
        with self.lock:
            del self.jobs[key]
            self._unqueue_job(key)

    # add job id to queue
    def _queue_job(self, key, urgent=False):
        if urgent:
            self.wait_queue.appendleft(key)
        else:
            self.wait_queue.append(key)

    # add job id to queue
    def queue_job(self, key, urgent=False):
        with self.lock:
            job = self.jobs[key]
            job.queue()
            self._queue_job(key, urgent)

    # removes an id0 from the job queue if it was queued before
    def _unqueue_job(self, key):
        if key in self.wait_queue:
            self.wait_queue.remove(key)

    # removes an id0 from the job queue, raises ValueError if it was not queued
    def unqueue_job(self, key):
        with self.lock:
            job = self.jobs[key]
            job.unqueue()
            self._unqueue_job(job.key)

    # pop from job queue, optionally filtering by type
    def _request_job(self, requested_types):
        if len(self.wait_queue) == 0:
            return
        for key in self.wait_queue:
            job = self.jobs[key]
            if job.type in requested_types:
                self.wait_queue.remove(key)
                subjob, requeue = job.get_job()
                if subjob:
                    if requeue:
                        self._queue_job(key)
                    return subjob

    # pop from job queue if not empty and assign, optionally filtering by type
    def request_job(self, requested_types, worker_name=None, worker_ip=None, worker_version=None):
        if requested_types == set(["fc-lfcs"]):
            worker_type = "friendbot"
        else:
            worker_type = "miiner"
        with self.lock:
            worker = self.update_worker(worker_name, worker_type, worker_ip, worker_version)
            job = self._request_job(requested_types)
            if job:
                job.assign(worker)
                return job

    # set job status back to waiting, KeyError if it does not exist
    def release_job(self, key, subkey=None):
        with self.lock:
            job = self.jobs[key]
            job.release(subkey)
            self._queue_job(key, urgent=True)

    # returns False if a job was canceled, updates its time/worker and returns True otherwise
    def update_job(self, key, subkey=None, worker_ip=None):
        with self.lock:
            job = self.jobs[key]
            if job.is_canceled():
                return False
            job.update(subkey)
            if job.assignee:
                self.update_worker(job.assignee.name, job.assignee.type, worker_ip)
            return True

    # if a name is provided, updates that worker's ip and time, creating one if necessary; returns the Worker object
    def update_worker(self, name, worker_type, ip=None, version=None):
        with self.lock:
            if name:
                if name in self.workers:
                    self.workers[name].update(worker_type, ip, version)
                else:
                    self.workers[name] = Worker(name, worker_type, ip, version)
                return self.workers[name]

    def _save_job_result(self, key, result):
        job = self.jobs[key]
        save_result(key, result, key_type=job.type)

    # save result to disk and delete job
    def complete_job(self, key, result, subkey=None):
        with self.lock:
            job = self.jobs[key]
            if subkey is not None or result is not None:
                job.complete(subkey)
                if result is not None:
                    # also complete main job if there's result and is sub job
                    if subkey is not None:
                        job.complete()
                    result = truncate_result(key, result)
                    self._save_job_result(key, result)
                    self.fulfill_dependents(key, result)
                    self.delete_job(key)

    # fulfill any jobs that have the given job as a prerequisite
    def fulfill_dependents(self, key, result):
        with self.lock:
            for job in self.jobs.values():
                # only chain jobs have prereqs
                if not isinstance(job, ChainJob):
                    continue
                # only fulfill dependents
                if not job.prereq_key == key:
                    continue
                # pass_prereq() is an enforced transition
                if not 'need_prereq' == job.state:
                    continue
                # pass result and queue job
                job.pass_prereq(result)
                self.queue_job(job.key)

    # mark job as failed and attach note
    def fail_job(self, key, subkey=None, note=None):
        with self.lock:
            job = self.jobs[key]
            job.fail(subkey, note)

    # auto-complete jobs that already have a result saved
    def autocomplete_jobs(self, keys):
        with self.lock:
            completed = []
            for key in keys:
                job = self.jobs[key]
                if job.is_already_done():
                    self._unqueue_job(job.key)
                    self.fulfill_dependents(job.key, read_result(job.key))
                    completed.append(job.key)
            for key in completed:
                self.delete_job(key)
            return completed

    # requeue dead jobs
    def release_dead_jobs(self):
        with self.lock:
            released = []
            for job in self.jobs.values():
                if job.is_working() and job.release_if_timed_out():
                    released.append(job.key)
            for key in released:
                self._queue_job(key, urgent=True)
            return released

    # delete old canceled jobs
    def trim_canceled_jobs(self):
        with self.lock:
            deleted = []
            for job in self.jobs.values():
                if job.is_canceled() and job.has_timed_out():
                    deleted.append(job.key)
            for key in deleted:
                self.delete_job(key)
            return deleted

    # True if current job exists
    def job_exists(self, key):
        with self.lock:
            return key in self.jobs

    # return job status if found, finished if movable exists, KeyError if neither
    def check_job_status(self, key, extra_info=False):
        with self.lock:
            try:
                job = self.jobs[key]
                return job.state
            except KeyError as e:
                if result_exists(key):
                    return 'done'
                return 'nonexistent'

    def get_mining_stats(self, key):
        with self.lock:
            job = self.jobs[key]
            mining_stats = {
                'assignee': job.get_assignee_name(),
                'rate': job.mining_rate,
                'offset': job.mining_offset
            }
            if 'msed' == job.type:
                mining_stats['lfcs'] = job.lfcs
            return mining_stats

    def get_chain_status(self, key):
        pass

    # returns all current jobs, optionally only those with a specific status
    def list_jobs(self, status_filter=None):
        with self.lock:
            if status_filter:
                return [j for j in self.jobs.values() if j.state == status_filter]
            else:
                return self.jobs.values()

    # returns the number of current jobs, optionally only counting those with a specific status
    def count_jobs(self, status_filter=None):
        return len(self.list_jobs(status_filter))

    # returns a list of workers, optionally filtered by activity or worker type
    def list_workers(self, active_only=False, filter_type=None):
        workers = []
        with self.lock:
            if not (active_only or filter_type):
                return self.workers.values()
            for worker in self.workers.values():
                if filter_type and worker.type != filter_type:
                    continue
                if active_only and not worker.has_timed_out():
                    workers.append(worker)
                elif not active_only:
                    workers.append(worker)
            return workers

    def list_miners(self, active_only=False):
        return self.list_workers(active_only, "miiner")

    def list_friendbots(self, active_only=False):
        return self.list_workers(active_only, "friendbot")

    # returns the number of workers, optionally only counting the active ones
    def count_workers(self, active_only=False):
        return len(self.list_workers(active_only))

    def count_miners(self, active_only=False):
        return len(self.list_miners(active_only))

    def count_friendbots(self, active_only=False):
        return len(self.list_friendbots(active_only))

# Generic mining job class
class Job(Machine):

    # states
    states = [
        'submitted',
        'ready',
        'waiting',
        'working',
        'canceled',
        'failed',
        'done'
    ]

    transitions = [
        {
            'trigger': 'queue',
            'source': 'ready',
            'dest': 'waiting'
        },
        {
            'trigger': 'unqueue',
            'source': 'waiting',
            'dest': 'ready'
        },
        {
            'trigger': '_assign',
            'source': 'waiting',
            'dest': 'working',
            'before': 'on_assign'
        },
        {
            'trigger': '_release',
            'source': 'working',
            'dest': 'waiting'
        },
        {
            'trigger': 'reset',
            'source': 'canceled',
            'dest': 'submitted'
        },
        {
            'trigger': '_fail',
            'source': 'working',
            'dest': 'failed',
            'before': 'on_fail'
        },
        {
            'trigger': '_complete',
            'source': ['waiting', 'working'],
            'dest': 'done'
        }
    ]

    # note that _type is used instead of just type (avoids keyword collision)
    def __init__(self, key, _type):
        super().__init__(
            states=Job.states,
            transitions=Job.transitions,
            initial='submitted'
        )
        # job properties
        self.key = key
        self.subkey = None
        self.type = _type
        self.note = None
        # for queue
        self.created = datetime.now(tz=timezone.utc)
        self.assignee = None
        self.last_update = self.created
        # mining stats
        self.mining_rate = None
        self.mining_offset = None

    def update(self, subkey=None):
        self.last_update = datetime.now(tz=timezone.utc)

    def assign(self, worker, subkey=None):
        self._assign(worker, subkey)

    def release(self, subkey=None):
        self._release(subkey)

    def fail(self, subkey=None, note=None):
        self._fail(subkey, note)

    def complete(self, subkey=None):
        self._complete(subkey)

    def on_assign(self, worker, subkey=None):
        self.assignee = worker
        self.update()

    def on_fail(self, subkey=None, note=None):
        self.note = note

    def is_already_done(self):
        if self.is_done():
            return True
        if read_result(self.key):
            self.to_done()
            return True
        return False

    # 2nd ret: False to not requeue main job
    def get_job(self):
        return self, False

    def get_assignee_name(self):
        return self.assignee.name if self.assignee else None

    # True if the job has timed out, False if it has not
    def has_timed_out(self):
        return datetime.now(tz=timezone.utc) > (self.last_update + job_lifetime)

    def release_if_timed_out(self):
        if self.has_timed_out():
            self.release()
            return True
        return False

    def __iter__(self):
        # job properties
        yield 'key', self.key
        yield 'type', self.type
        yield 'status', self.state
        yield 'note', self.note
        # for queue
        yield 'created', self.created.isoformat()
        yield 'assignee', self.get_assignee_name()
        yield 'last_update', self.last_update.isoformat()
        # mining stats
        yield 'mining_rate', self.mining_rate
        yield 'mining_offset', self.mining_offset


# Job class for jobs that are only ready once another job supplies a prerequisite
class ChainJob(Job):

    def __init__(self, key, _type, prereq_key):
        super().__init__(key, _type)
        self.add_state('need_prereq')
        self.add_transition('prepare', 'submitted', 'need_prereq', after='on_prepare')
        self.add_transition('pass_prereq', 'need_prereq', 'ready', before='on_pass_prereq')
        # chain-specific job properties
        self.prereq_key = prereq_key

    def on_prepare(self):
        if not self.prereq_key:
            self.to_ready()

    def __iter__(self):
        yield from super().__iter__()
        yield 'prereq_key', self.prereq_key


# Job to obtain LFCS from the system ID in Mii data
class MiiLfcsJob(Job):

    def __init__(self, system_id, model, year):
        super().__init__(system_id, 'mii-lfcs')
        self.add_transition('prepare', 'submitted', 'ready', before='on_prepare')
        # mii-specific job properties
        self.console_model = model
        self.console_year = year
        # dummy distributed mining info
        self.model_bytes = None
        # mii jobs are ready immediately
        if not self.is_already_done():
            self.prepare()

    def on_prepare(self):
        # init distributed mining info
        start_lfcs, self.model_bytes, lfcs_min, lfcs_max = get_lfcs_start_range_flags(self.console_model, self.console_year)
        self.lfcs_base = lfcs_min
        self.lfcs_count = lfcs_max - lfcs_min
        self.lfcs_istart = start_lfcs - lfcs_min
        # should use ceil... but this works
        self.progress = bytearray(self.lfcs_count // 8 + 1)
        self.mining = {}

    def check_progress(self, idx):
        return self.progress[idx // 8] >> (idx % 8) & 0x1

    def update_progress(self, idx, val):
        pi = idx // 8
        bi = idx % 8
        self.progress[pi] &= ~(0b1 << bi)
        self.progress[pi] |= (1 if val else 0) << bi

    def get_next_idx(self):
        offset = 0
        min_reached = False
        max_reached = False
        while not min_reached or not max_reached:
            idx = self.lfcs_istart + offset
            if idx < 0:
                min_reached = True
            elif idx > self.lfcs_count:
                max_reached = True
            else:
                if not self.check_progress(idx):
                    return idx
            if offset == 0:
                offset = 1
            elif offset > 0:
                offset = -offset
            elif offset < 0:
                offset = -offset + 1
        return None

    def assign(self, worker, subkey=None):
        if subkey in self.mining:
            # this actually will never be run
            self.mining[subkey].assign(worker)
        elif subkey is None:
            super().assign(worker, subkey)

    def release(self, subkey=None):
        if subkey in self.mining:
            subjob = self.mining.pop(subkey)
            self.update_progress(subjob.idx, 0)
        elif subkey is None:
            super().release(subkey)

    def fail(self, subkey=None, note=None):
        if subkey in self.mining:
            subjob = self.mining.pop(subkey)
            # currently treat it the same as release
            self.update_progress(subjob.idx, 0)
        elif subkey is None:
            super().fail(subkey, note)

    def complete(self, subkey=None):
        if subkey in self.mining:
            del self.mining[subkey]
        elif subkey is None:
            super().complete(subkey)

    # 2nd ret: True to requeue main job
    def get_job(self):
        idx = self.get_next_idx()
        if idx:
            if self.is_waiting():
                self.to_working()
            self.update_progress(idx, 1)
            subjob = MiiLfcsOffsetJob(self, self.lfcs_base + idx, idx)
            self.mining[subjob.subkey] = subjob
            return subjob, True
        return None, False

    def __iter__(self):
        yield from super().__iter__()
        yield 'model', self.console_model
        yield 'year', self.console_year
        yield 'model_bytes', self.model_bytes.hex()
        yield 'system_id', self.key


# per offset sub-job of MiiLfcsJob
class MiiLfcsOffsetJob(Job):

    def __init__(self, _parent, offset, idx):
        super().__init__(_parent.key, 'mii-lfcs-offset')
        self._parent = _parent
        if type(offset) == int:
            self.subkey = offset.to_bytes(2, 'big').hex()
        else:
            self.subkey = offset
        self.idx = idx
        # working immediately
        self.to_waiting()

    # True if the job has timed out, False if it has not
    def has_timed_out(self):
        return datetime.now(tz=timezone.utc) > (self.last_update + job_lifetime)

    def __iter__(self):
        # might need to completely rewrite iter or select partially feilds
        yield from self._parent.__iter__()
        yield 'offset', self.subkey


# Job to obtain LFCS from a friend exchange
class FcLfcsJob(Job):

    def __init__(self, friend_code):
        super().__init__(friend_code, 'fc-lfcs')
        self.add_transition('prepare', 'submitted', 'ready')
        # fc-specific job properties
        self.friend_code = friend_code
        # fc jobs are ready immediately
        if not self.is_already_done():
            self.prepare()

    def __iter__(self):
        yield from super().__iter__()
        yield 'friend_code', self.key


# Job to obtain movable.sed using a LFCS (part1 file)
class MsedJob(ChainJob):

    def __init__(self, id0, lfcs=None, prereq_key=None):
        super().__init__(id0, 'msed', prereq_key)
        if not prereq_key and not lfcs:
            raise ValueError('Must supply either a LFCS or a prerequisite job key')
        # msed-specific job properties
        self.lfcs = lfcs
        if not self.is_already_done():
            self.prepare()

    def on_prepare(self):
        # msed jobs need lfcs first
        if self.lfcs:
            self.to_ready()
    
    def on_pass_prereq(self, lfcs):
        self.lfcs = hexlify(lfcs).decode('ascii')

    def has_lfcs(self):
        if self.lfcs:
            return True
        else:
            return False

    def __iter__(self):
        yield from super().__iter__()
        yield 'id0', self.key
        yield 'lfcs', self.lfcs


class Worker():

    def __init__(self, name, worker_type, ip=None, version=None):
        self.name = name
        self.ip = ip
        self.type = worker_type
        self.version = version
        self.update()

    def update(self, worker_type=None, ip=None, version=None):
        self.last_update = datetime.now(tz=timezone.utc)
        if worker_type:
            self.type = worker_type
        if ip:
            self.ip = ip
        if version:
            self.version = version

    # True if the worker has timed out, False if they have not
    def has_timed_out(self):
        return datetime.now(tz=timezone.utc) > (self.last_update + worker_lifetime)

    def __iter__(self):
        yield 'name', self.name
        yield 'ip', self.ip
        yield 'version', self.version
        yield 'last_update', self.last_update.isoformat()


# mii mining related helper
def get_lfcs_start_range_flags(model, year):
    if 'old' == model:
        model_bytes = b'\x00\x00'
        start_lfcs = lfcs_starts_old.get(year, lfcs_default_old)
        lfcs_min = lfcs_min_old
        lfcs_max = lfcs_max_old
    elif 'new' == model:
        model_bytes = b'\x02\x00'
        start_lfcs = lfcs_starts_new.get(year, lfcs_default_new)
        lfcs_min = lfcs_min_new
        lfcs_max = lfcs_max_new
    else:
        raise ValueError('Invalid model')
    return start_lfcs >> 16, model_bytes, lfcs_min >> 16, lfcs_max >> 16


# lfcs storage by system id

def system_id_to_lfcs_path(system_id, create=False):
    lfcs_dir = os.path.join(sid_lfcses_path, f'{system_id[0:2]}/{system_id[2:4]}')
    if create:
        os.makedirs(lfcs_dir, exist_ok=True)
    return os.path.join(lfcs_dir, system_id)

def sid_lfcs_exists(system_id):
    lfcs_path = system_id_to_lfcs_path(system_id)
    return os.path.isfile(lfcs_path)

def sid_save_lfcs(system_id, lfcs):
    with open(system_id_to_lfcs_path(system_id, create=True), 'wb') as lfcs_file:
        lfcs_file.write(lfcs)

def sid_read_lfcs(system_id):
    if not sid_lfcs_exists(system_id):
        return
    with open(system_id_to_lfcs_path(system_id), 'rb') as lfcs_file:
        lfcs = lfcs_file.read()
        if len(lfcs) < 5: # broken file?
            return
        else:
            return lfcs[:5]


# lfcs storage by friend code

def friend_code_to_lfcs_path(friend_code, create=False):
    lfcs_dir = os.path.join(fc_lfcses_path, f'{friend_code[0:2]}/{friend_code[2:4]}')
    if create:
        os.makedirs(lfcs_dir, exist_ok=True)
    return os.path.join(lfcs_dir, friend_code)

def fc_lfcs_exists(friend_code):
    lfcs_path = friend_code_to_lfcs_path(friend_code)
    return os.path.isfile(lfcs_path)

def fc_save_lfcs(friend_code, lfcs):
    with open(friend_code_to_lfcs_path(friend_code, create=True), 'wb') as lfcs_file:
        lfcs_file.write(lfcs)

def fc_read_lfcs(friend_code):
    if not fc_lfcs_exists(friend_code):
        return
    with open(friend_code_to_lfcs_path(friend_code), 'rb') as lfcs_file:
        lfcs = lfcs_file.read()
        if len(lfcs) < 5: # broken file?
            return
        else:
            return lfcs[:5]


# msed storage by id0

def id0_to_movable_path(id0, create=False):
    movable_dir = os.path.join(mseds_path, f'{id0[0:2]}/{id0[2:4]}')
    if create:
        os.makedirs(movable_dir, exist_ok=True)
    return os.path.join(movable_dir, id0)

def movable_exists(id0):
    movable_path = id0_to_movable_path(id0)
    return os.path.isfile(movable_path)

def save_movable(id0, movable):
    with open(id0_to_movable_path(id0, create=True), 'wb') as movable_file:
        movable_file.write(movable)

def read_movable_from_bfm_site(id0):
    try:
        # bfm backend average response time is 2.5s~3s from personal test
        r = HTMLSession().post(bfm_site_base + bfm_site_endpoint, data={'searchterm': id0}, timeout=5)
        a = r.html.find('a[href^="/get_movable"]', first=True)
        if a:
            # getting movable is very fast, 1s is probably too much
            r = requests.get(bfm_site_base + a.attrs['href'], timeout=1)
            if r.status_code == 200:
                movable = r.content  # size can be either 0x120 or 0x140
                length = r.headers['content-length']
                if length and len(movable) != int(length):
                    return None
                try:
                    return r.content[0x110:0x120]
                except IndexError as e:
                    return None

    except:
        return None

def read_movable(id0):
    if not movable_exists(id0):
        bfm_movable = read_movable_from_bfm_site(id0)
        if bfm_movable:
            save_movable(id0, bfm_movable)
            return bfm_movable
        else:
            return

    with open(id0_to_movable_path(id0), 'rb') as movable_file:
        movable = movable_file.read()
        if len(movable) == 0x10: # reduced size
            return b"\0" * 0x110 + movable + b"\0" * 0x20
        elif len(movable) == 0x140: # old full size
            return movable
        else: # broken file?
            return


def result_exists(key, key_type=None):
    if not key_type:
        key_type = get_key_type(key)
    if 'fc-lfcs' == key_type and fc_lfcs_exists(key):
        return 'done'
    elif 'mii-lfcs' == key_type and sid_lfcs_exists(key):
        return 'done'
    elif 'msed' == key_type and movable_exists(key):
        return 'done'

def read_result(key, key_type=None):
    if not key_type:
        key_type = get_key_type(key)
    if 'fc-lfcs' == key_type:
        return fc_read_lfcs(key)
    elif 'mii-lfcs' == key_type:
        return sid_read_lfcs(key)
    elif 'msed' == key_type:
        return read_movable(key)

def save_result(key, result, key_type=None):
    if not key_type:
        key_type = get_key_type(key)
    if 'fc-lfcs' == key_type:
        fc_save_lfcs(key, result)
    elif 'mii-lfcs' == key_type:
        sid_save_lfcs(key, result)
    elif 'msed' == key_type:
        save_movable(key, result)

def truncate_result(key, result, key_type=None):
    if not key_type:
        key_type = get_key_type(key)
    if 'fc-lfcs' == key_type:
        return result[:5]
    elif 'mii-lfcs' == key_type:
        return result[:5]
    elif 'msed' == key_type:
        return result


def count_lfcses_mined():
    return sum(len(files) for _, _, files in os.walk(sid_lfcses_path))

def count_lfcses_dumped():
    return sum(len(files) for _, _, files in os.walk(fc_lfcses_path))

def count_mseds_mined():
    return sum(len(files) for _, _, files in os.walk(mseds_path))
