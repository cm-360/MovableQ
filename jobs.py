from transitions import Machine

from collections import deque
from datetime import datetime, timedelta, timezone
import base64
import json
import os
from threading import RLock
from binascii import hexlify

from validators import is_id0, is_system_id, is_friend_code


fc_lfcses_path = os.getenv('FC_LFCSES_PATH', './lfcses/fc')
sid_lfcses_path = os.getenv('SID_LFCSES_PATH', './lfcses/sid')
mseds_path = os.getenv('MSEDS_PATH', './mseds')

job_lifetime = timedelta(minutes=5)
worker_lifetime = timedelta(minutes=10)


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
                if overwrite_canceled and 'canceled' == self.jobs[job.key].state:
                    self.delete_job(job.key)
                else:
                    raise ValueError(f'Duplicate job: {job.key}')
            self.jobs[job.key] = job

    def submit_job_chain(self, chain, overwrite_canceled=False):
        with self.lock:
            to_delete = []
            # loop twice so we submit no jobs if any are duplicates
            for job in chain:
                if not self.job_exists(job.key):
                    continue
                if overwrite_canceled and 'canceled' == self.jobs[job.key].state:
                    to_delete.append(job.key)
                else:
                    raise ValueError(f'Duplicate job: {job.key}')
            for key in to_delete:
                self.delete_job(key)
            for job in chain:
                self.jobs[job.key] = job

    # adds a part1 file to a job
    def add_part1(self, id0, part1):
        with self.lock:
            job = self.jobs[id0]
            if job.prerequisite and self.job_exists(job.prerequisite):
                self.cancel_job(job.prerequisite)
            job.add_part1(part1)

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
            if 'ready' == job.state:
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

    # add job id to queue, raises ValueError if it was already queued
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
                return job

    # pop from job queue if not empty and assign, optionally filtering by type
    def request_job(self, requested_types, worker_name=None, worker_ip=None):
        if requested_types == set(["fc"]):
            worker_type = "friendbot"
        else:
            worker_type = "miiner"
        with self.lock:
            worker = self.update_worker(worker_name, worker_type, worker_ip)
            job = self._request_job(requested_types)
            if job:
                job.assign(worker)
                return job

    # set job status to canceled, KeyError if it does not exist
    def release_job(self, key):
        with self.lock:
            job = self.jobs[key]
            job.release()
            self._queue_job(key, urgent=True)

    # returns False if a job was canceled, updates its time/worker and returns True otherwise
    def update_job(self, key, worker_ip=None):
        with self.lock:
            job = self.jobs[key]
            if 'canceled' == job.state:
                return False
            job.update()
            if job.assignee:
                self.update_worker(job.assignee.name, job.assignee.type, worker_ip)
            return True

    # if a name is provided, updates that worker's ip and time, creating one if necessary; returns the Worker object
    def update_worker(self, name, worker_type, ip=None):
        with self.lock:
            if name:
                if name in self.workers:
                    self.workers[name].update(worker_type, ip)
                else:
                    self.workers[name] = Worker(name, worker_type, ip)
                return self.workers[name]

    def _save_job_result(self, key, result):
        job = self.jobs[key]
        if 'mii' == job.type:
            sid_save_lfcs(key, result)
        elif 'fc' == job.type:
            fc_save_lfcs(key, result)
        elif 'part1' == job.type:
            save_movable(key, result)

    # save result to disk and delete job
    def complete_job(self, key, result):
        with self.lock:
            job = self.jobs[key]
            job.complete()
            self._save_job_result(key, result)
            self.fulfill_dependents(key, result)
            self.delete_job(key)

    # fulfill any jobs that have the given job as a prerequisite
    def fulfill_dependents(self, key, result):
        with self.lock:
            for job in self.jobs.values():
                if isinstance(job, ChainJob) and job.prereq_key == key:
                    job.pass_prereq(result)
                    self.queue_job(job.key)
            # str(base64.b64encode(part1), 'utf-8')

    # mark job as failed and attach note
    def fail_job(self, key, note=None):
        with self.lock:
            job = self.jobs[key]
            job.fail(note)

    # requeue dead jobs
    def release_dead_jobs(self):
        with self.lock:
            released = []
            for job in self.jobs.values():
                if 'working' == job.state and job.has_timed_out():
                    job.release()
                    released.append(job.key)
            for key in released:
                self._queue_job(key, urgent=True)
            return released

    # delete old canceled jobs
    def trim_canceled_jobs(self):
        with self.lock:
            deleted = []
            for job in self.jobs.values():
                if 'canceled' == job.state and job.has_timed_out():
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
                if is_friend_code(key) and fc_lfcs_exists(key):
                    return 'done'
                elif is_system_id(key) and sid_lfcs_exists(key):
                    return 'done'
                elif is_id0(key) and movable_exists(key):
                    return 'done'
                else:
                    raise e

    def get_mining_stats(self, key):
        with self.lock:
            job = self.jobs[key]
            return {
                'assignee': job.get_assignee_name(),
                'rate': job.mining_rate,
                'offset': job.mining_offset
            }

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
            'trigger': 'assign',
            'source': 'waiting',
            'dest': 'working',
            'before': 'on_assign'
        },
        {
            'trigger': 'release',
            'source': 'working',
            'dest': 'waiting'
        },
        {
            'trigger': 'reset',
            'source': 'canceled',
            'dest': 'submitted'
        },
        {
            'trigger': 'fail',
            'source': 'working',
            'dest': 'failed',
            'before': 'on_fail'
        },
        {
            'trigger': 'complete',
            'source': 'working',
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
        self.type = _type
        self.note = None
        # for queue
        self.created = datetime.now(tz=timezone.utc)
        self.assignee = None
        self.last_update = self.created
        # mining stats
        self.mining_rate = None
        self.mining_offset = None

    def update(self):
        self.last_update = datetime.now(tz=timezone.utc)

    def on_assign(self, worker):
        self.assignee = worker
        self.update()

    def on_fail(self, note=None):
        self.note = note

    def get_assignee_name(self):
        return self.assignee.name if self.assignee else None

    # True if the job has timed out, False if it has not
    def has_timed_out(self):
        return datetime.now(tz=timezone.utc) > (self.last_update + job_lifetime)

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


# Job to obtain movable_part1.sed from the LFCS hash in Mii data
class MiiJob(Job):

    def __init__(self, system_id, model, year):
        super().__init__(system_id, 'mii')
        self.add_transition('prepare', 'submitted', 'ready')
        # mii-specific job properties
        self.console_model = model
        self.console_year = year
        # mii jobs are ready immediately
        self.prepare()

    def __iter__(self):
        yield from super().__iter__()
        yield 'model', self.console_model
        yield 'year', self.console_year
        yield 'system_id', self.key


# Job to obtain movable_part1.sed from a friend exchange
class FCJob(Job):

    def __init__(self, friend_code):
        super().__init__(friend_code, 'fc')
        self.add_transition('prepare', 'submitted', 'ready')
        # fc-specific job properties
        self.friend_code = friend_code
        # fc jobs are ready immediately
        self.prepare()

    def __iter__(self):
        yield from super().__iter__()
        yield 'friend_code', self.key


# Job to obtain movable.sed using a part1 file
class Part1Job(ChainJob):

    def __init__(self, id0, lfcs=None, prereq_key=None):
        super().__init__(id0, 'part1', prereq_key)
        if not prereq_key and not lfcs:
            raise ValueError('Must supply either a LFCS or a prerequisite job key')
        # part1-specific job properties
        self.lfcs = lfcs
        # part1 jobs need part1 (duh)
        self.prepare()

    def on_prepare(self):
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

    def __init__(self, name, worker_type, ip=None):
        self.name = name
        self.ip = ip
        self.type = worker_type
        self.update()

    def update(self, worker_type=None, ip=None):
        if worker_type is None:
            worker_type = self.type
        self.last_update = datetime.now(tz=timezone.utc)
        self.type = worker_type
        if ip:
            self.ip = ip

    # True if the worker has timed out, False if they have not
    def has_timed_out(self):
        return datetime.now(tz=timezone.utc) > (self.last_update + worker_lifetime)

    def __iter__(self):
        yield 'name', self.name
        yield 'ip', self.ip
        yield 'last_update', self.last_update.isoformat()


# lfcs storage by system id

def system_id_to_lfcs_path(system_id, create=False):
    lfcs_dir = os.path.join(sid_lfcses_path, f'{system_id[0:2]}/{system_id[2:4]}')
    if create:
        os.makedirs(lfcs_dir, exist_ok=True)
    return os.path.join(lfcs_dir, system_id)

def sid_lfcs_exists(system_id):
    lfcs_path = system_id_to_lfcs_path(system_id)
    print(lfcs_path, os.path.isfile(lfcs_path))
    return os.path.isfile(lfcs_path)

def sid_save_lfcs(system_id, lfcs):
    with open(system_id_to_lfcs_path(system_id, create=True), 'wb') as lfcs_file:
        lfcs_file.write(lfcs)

def sid_read_lfcs(system_id):
    if not lfcs_exists(system_id):
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
    if not lfcs_exists(friend_code):
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

def read_movable(id0):
    if not movable_exists(id0):
        return
    with open(id0_to_movable_path(id0), 'rb') as movable_file:
        movable = movable_file.read()
        if len(movable) == 0x10: # reduced size
            return b"\0" * 0x110 + movable + b"\0" * 0x20
        elif len(movable) == 0x140: # old full size
            return movable
        else: # broken file?
            return


def count_lfcses_mined():
    return sum(len(files) for _, _, files in os.walk(sid_lfcses_path))

def count_lfcses_dumped():
    return sum(len(files) for _, _, files in os.walk(fc_lfcses_path))

def count_mseds_mined():
    return sum(len(files) for _, _, files in os.walk(mseds_path))
