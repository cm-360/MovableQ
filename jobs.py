from transitions import Machine

from collections import deque
from datetime import datetime, timedelta, timezone
import json
import os
from threading import RLock


movable_path = os.getenv('MSEDS_PATH', './mseds')
job_lifetime = timedelta(minutes=5)
miner_lifetime = timedelta(minutes=10)


class JobManager():

    def __init__(self):
        self.jobs = {}
        self.wait_queue = deque()
        self.miners = {}
        self.lock = RLock()

    # adds a job to the current job list, raises a ValueError if it exists already
    def submit_job(self, job):
        with self.lock:
            if self.job_exists(job.id0):
                raise ValueError(f'Duplicate job: {job.id0}')
            self.jobs[job.id0] = job

    # adds a part1 file to a job
    def add_part1(self, id0, part1):
        with self.lock:
            self.jobs[id0].add_part1(part1)

    # set job status to canceled, KeyError if it does not exist
    def cancel_job(self, id0):
        with self.lock:
            job = self.jobs[id0]
            job.to_canceled()
            self._unqueue_job(id0)

    # reset a canceled job
    def reset_job(self, id0):
        with self.lock:
            job = self.jobs[id0]
            job.reset()
            job.prepare()
            if 'ready' == job.state:
                self._queue_job(id0)

    # delete job from the current job list if exists
    def delete_job(self, id0):
        with self.lock:
            del self.jobs[id0]
            self._unqueue_job(id0)

    # add job id to queue
    def _queue_job(self, id0, urgent=False):
        if urgent:
            self.wait_queue.appendleft(id0)
        else:
            self.wait_queue.append(id0)

    # add job id to queue, raises ValueError if it was already queued
    def queue_job(self, id0, urgent=False):
        with self.lock:
            job = self.jobs[id0]
            job.queue()
            self._queue_job(id0, urgent)

    # removes an id0 from the job queue if it was queued before
    def _unqueue_job(self, id0):
        if id0 in self.wait_queue:
            self.wait_queue.remove(id0)

    # removes an id0 from the job queue, raises ValueError if it was not queued
    def unqueue_job(self, id0):
        with self.lock:
            job = self.jobs[id0]
            job.unqueue()
            self._unqueue_job(job.id0)

    # pop from job queue, optionally filtering by type
    def _get_job(self, accepted_types=None):
        if len(self.wait_queue) == 0:
            return
        if accepted_types:
            for id0 in self.wait_queue:
                job = self.jobs[id0]
                if job.type in accepted_types:
                    self.wait_queue.remove(id0)
                    return job
        else:
            return self.jobs[self.wait_queue.popleft()]

    # pop from job queue if not empty and assign, optionally filtering by type
    def request_job(self, miner_name=None, miner_ip=None, accepted_types=None):
        with self.lock:
            miner = self.update_miner(miner_name, miner_ip)
            job = self._get_job(accepted_types)
            if job:
                job.assign(miner)
                return job

    # set job status to canceled, KeyError if it does not exist
    def release_job(self, id0):
        with self.lock:
            job = self.jobs[id0]
            job.release()
            self._queue_job(id0, urgent=True)

    # returns False if a job was canceled, updates its time/miner and returns True otherwise
    def update_job(self, id0, miner_ip=None):
        with self.lock:
            job = self.jobs[id0]
            if job.canceled:
                return False
            job.update()
            if job.assignee:
                self.update_miner(job.assignee.name, miner_ip)
            return True

    # if a name is provided, updates that miners ip and time, creating one if necessary; returns the Miner object
    def update_miner(self, name, ip=None):
        with self.lock:
            if name:
                if name in self.miners:
                    self.miners[name].update(ip)
                else:
                    self.miners[name] = Miner(name, ip)
                return self.miners[name]

    # save movable to disk and delete job
    def complete_job(self, id0, movable):
        with self.lock:
            job = self.jobs[id0]
            job.complete()
            save_movable(id0, movable)
            self.delete_job(id0)

    # requeue dead jobs
    def release_dead_jobs(self):
        with self.lock:
            released = []
            for job in self.jobs.values():
                if 'working' == job.state and job.has_timed_out():
                    job.release()
                    released.append(job.id0)
            for id0 in released:
                self._queue_job(id0, urgent=True)
            return released

    # delete old canceled jobs
    def trim_canceled_jobs(self):
        with self.lock:
            deleted = []
            for job in self.jobs.values():
                if 'canceled' == job.state and job.has_timed_out():
                    deleted.append(job.id0)
            for id0 in deleted:
                self.delete_job(id0)
            return deleted

    # True if current job exists
    def job_exists(self, id0):
        with self.lock:
            return id0 in self.jobs

    # return job status if found, finished if movable exists, KeyError if neither
    def check_job_status(self, id0):
        with self.lock:
            try:
                job = self.jobs[id0]
                return job.state
            except KeyError as e:
                if movable_exists(id0):
                    return 'done'
                else:
                    raise e

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

    # returns a list of all miners, or optionally only the active ones
    def list_miners(self, active_only=False):
        with self.lock:
            if active_only:
                return [m for m in self.miners.values() if not m.has_timed_out()]
            else:
                return self.miners.values()

    # returns the number of miners, optionally only counting the active ones
    def count_miners(self, active_only=False):
        return len(self.list_miners(active_only))


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
    def __init__(self, id0, _type):
        super().__init__(
            states=Job.states,
            transitions=Job.transitions,
            initial='submitted'
        )
        # job properties
        self.id0 = id0
        self.type = _type
        self.note = None
        # for queue
        self.canceled = False
        self.created = datetime.now(tz=timezone.utc)
        self.assignee = None
        self.last_update = self.created

    def update(self):
        self.last_update = datetime.now(tz=timezone.utc)

    def on_assign(self, miner):
        self.assignee = miner
        self.update()

    def on_fail(self, note=None):
        self.note = note

    # True if the job has timed out, False if it has not
    def has_timed_out(self):
        return datetime.now(tz=timezone.utc) > (self.last_update + job_lifetime)

    def __iter__(self):
        yield 'type', self.type
        yield 'id0', self.id0
        yield 'status', self.state
        yield 'canceled', self.canceled
        yield 'created', self.created.isoformat()
        yield 'assignee', self.assignee.name if self.assignee else None
        yield 'last_update', self.last_update.isoformat()


class MiiJob(Job):

    def __init__(self, id0, model, year, mii):
        super().__init__(id0, 'mii')
        self.add_transition('prepare', 'submitted', 'ready')
        # mii-specific job properties
        self.console_model = model
        self.console_year = year
        self.mii = mii
        # mii jobs are ready immediately
        self.prepare()

    def __iter__(self):
        yield from super().__iter__()
        yield 'model', self.console_model
        yield 'year', self.console_year
        yield 'mii', self.mii


class Part1Job(Job):

    def __init__(self, id0, friend_code=None, part1=None):
        super().__init__(id0, 'part1')
        self.add_state('need_part1')
        self.add_transition('prepare', 'submitted', 'need_part1', after='on_prepare')
        self.add_transition('add_part1', 'need_part1', 'ready', before='on_add_part1')
        # part1-specific job properties
        self.friend_code = friend_code
        self.part1 = part1
        # part1 jobs need part1 (duh)
        self.prepare(part1)

    def on_prepare(self, part1=None):
        if part1:
            self.add_part1(part1)
        elif self.part1:
            self.to_ready()
    
    def on_add_part1(self, part1):
        self.part1 = part1

    def has_part1(self):
        if self.part1:
            return True
        else:
            return False

    def __iter__(self):
        yield from super().__iter__()
        yield 'friend_code', self.friend_code
        yield 'part1', self.part1


class Miner():

    def __init__(self, name, ip=None):
        self.name = name
        self.ip = ip
        self.update()

    def update(self, ip=None):
        self.last_update = datetime.now(tz=timezone.utc)
        if ip:
            self.ip = ip

    # True if the miner has timed out, False if they have not
    def has_timed_out(self):
        return datetime.now(tz=timezone.utc) > (self.last_update + miner_lifetime)

    def __iter__(self):
        yield 'name', self.name
        yield 'ip', self.ip
        yield 'last_update', self.last_update.isoformat()


def id0_to_movable_path(id0, create=False):
    dir = os.path.join(movable_path, f'{id0[0:2]}/{id0[2:4]}')
    if create:
        os.makedirs(dir, exist_ok=True)
    return os.path.join(dir, id0)

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
        return movable_file.read()

def count_total_mined():
    return sum(len(files) for _, _, files in os.walk(movable_path))
