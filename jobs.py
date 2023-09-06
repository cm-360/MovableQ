from collections import deque
from datetime import datetime, timedelta, timezone
import json
import os
from threading import RLock


movable_path = 'saved'
job_lifetime = timedelta(minutes=5)
miner_lifetime = timedelta(minutes=10)


class JobManager():

    def __init__(self):
        self.jobs = {}
        self.wait_queue = deque()
        self.miners = {}
        self.lock = RLock()

    # create and queue job if not exist
    def submit_job(self, job):
        with self.lock:
            if self.job_exists(job.id0):
                return False
            self.jobs[job.id0] = job
            self.queue_job(job.id0)
            return True

    # set job status to canceled if exists
    def cancel_job(self, id0):
        with self.lock:
            if not self.job_exists(id0):
                return False
            self.unqueue_job(id0)
            self.jobs[id0].status = 'canceled'
            return True

    # delete job from memory if exists
    def delete_job(self, id0):
        with self.lock:
            if not self.job_exists(id0):
                return False
            self.unqueue_job(id0)
            del self.jobs[id0]
            return True

    # add job id to queue if exists
    def queue_job(self, id0, urgent=False):
        with self.lock:
            if not self.job_exists(id0):
                return False
            self.jobs[id0].status = 'waiting'
            if id0 in self.wait_queue:
                return False
            if urgent:
                self.wait_queue.appendleft(id0)
            else:
                self.wait_queue.append(id0)
            return True

    def unqueue_job(self, id0):
        with self.lock:
            if id0 in self.wait_queue:
                self.wait_queue.remove(id0)
                return True
            return False

    # pop from job queue if not empty and assign
    def request_job(self, miner_name=None, miner_ip=None):
        with self.lock:
            self.update_miner(miner_name, miner_ip)
            if len(self.wait_queue) > 0:
                job = self.jobs[self.wait_queue.popleft()]
                job.status = 'working'
                job.assign_to(miner_name)
                return job

    # requeue dead jobs
    def release_dead_jobs(self):
        with self.lock:
            released = []
            for job in self.jobs.values():
                if job.status == 'working' and not job.is_alive():
                    released.append(job.id0)
            for id0 in released:
                self.queue_job(id0, urgent=True)
            return released

    def trim_canceled_jobs(self):
        with self.lock:
            deleted = []
            for job in self.jobs.values():
                if job.status == 'canceled' and not job.is_alive():
                    deleted.append(id0)
            for id0 in deleted:
                self.delete_job(id0)
            return deleted

    # True if current job exists
    def job_exists(self, id0):
        with self.lock:
            return id0 in self.jobs

    # return job status if found, finished if movable exists
    def check_job_status(self, id0):
        with self.lock:
            if self.job_exists(id0):
                return self.jobs[id0].status
            elif movable_exists(id0):
                return 'done'

    def list_jobs(self, status_filter=None):
        with self.lock:
            if status_filter:
                return [j for j in self.jobs.values() if j.status == status_filter]
            else:
                return self.jobs.values()

    def count_jobs(self, status_filter=None):
        return len(self.list_jobs(status_filter))

    def list_miners(self):
        with self.lock:
            return self.miners.values()

    def count_miners(self):
        return len(self.list_miners())

    # return 'canceled' if job was canceled, update time otherwise
    def update_job(self, id0, miner_ip=None):
        with self.lock:
            if not self.job_exists(id0):
                return False
            job = self.jobs[id0]
            if job.status == 'canceled':
                return 'canceled'
            else:
                job.update()
                self.update_miner(job.assignee, miner_ip)
                return True

    # save movable to disk and delete job
    def complete_job(self, id0, movable):
        with self.lock:
            if not self.job_exists(id0):
                return False
            save_movable(id0, movable)
            self.delete_job(id0)
            return True

    def update_miner(self, name, ip=None):
        with self.lock:
            if name:
                if name in self.miners:
                    self.miners[name].update(ip)
                else:
                    self.miners[name] = Miner(name, ip)


class Job():

    def __init__(self, id0, model, year, mii):
        # job properties
        self.id0 = id0
        self.model = model
        self.year = year
        self.mii = mii
        # for queue
        self.status = None
        self.created = datetime.now(tz=timezone.utc)
        self.assignee = None
        self.last_update = self.created
        # for authentication
        # self.token = None

    def assign_to(self, name):
        self.assignee = name
        self.update()

    def update(self):
        self.last_update = datetime.now(tz=timezone.utc)

    def is_alive(self):
        return datetime.now(tz=timezone.utc) < (self.last_update + job_lifetime)

    def __iter__(self):
        yield 'id0', self.id0
        yield 'model', self.model
        yield 'year', self.year
        yield 'mii', self.mii
        yield 'status', self.status
        yield 'created', self.created.isoformat()
        yield 'assignee', self.assignee
        yield 'last_update', self.last_update.isoformat()


class Miner():

    def __init__(self, name, ip=None):
        self.name = name
        self.ip = ip
        self.update()

    def update(self, ip=None):
        self.last_update = datetime.now(tz=timezone.utc)
        if ip:
            self.ip = ip

    def is_alive(self):
        return datetime.now(tz=timezone.utc) < (self.last_update + miner_lifetime)

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
