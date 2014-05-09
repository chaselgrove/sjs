# See file COPYING distributed with sjs for copyright and license.

import os
import sys
import traceback
import signal
import string
import datetime
import time
import subprocess
import sqlite3

class SJSError(Exception):

    """base class for ssggee errors

    derived classes should define __str__ in a way that is appropriate 
    to print as an error for the user
    """

class SJSROOTError(SJSError):

    """SJS_ROOT undefined or not a directory"""

    def __init__(self, error):
        SJSError.__init__(self)
        self.error = error

    def __str__(self):
        return 'SJS_ROOT is %s' % self.error

class Cluster:

    def __init__(self):
        self.sjs_root = os.path.abspath(os.environ['SJS_ROOT'])
        if not 'SJS_ROOT' in os.environ:
            raise SJSROOTError('not defined')
        if not os.path.isdir(os.environ['SJS_ROOT']):
            raise SJSROOTError('not a directory')
        slots_fname = os.path.join(self.sjs_root, 'slots')
        slots = open(slots_fname).read().strip()
        self.slots = int(slots)
        assert self.slots > 0
        return

    def log(self, msg):
        t = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        fo = open(os.path.join(self.sjs_root, 'log'), 'a')
        fo.write('%s  %s\n' % (t, msg))
        fo.close()
        return

    def submit(self, name, shell, script, script_args, stdout, stderr):
        db = sqlite3.connect(os.path.join(self.sjs_root, 'db.sqlite'))
        insert_query = """INSERT INTO job (user, 
                                           name, 
                                           shell, 
                                           script, 
                                           error_flag, 
                                           stdout, 
                                           stderr, 
                                           t_submit)
                          VALUES (?, ?, ?, ?, ?, ?, ?, ?)"""
        arg_query = """INSERT INTO argument (job_id, ordinal, argument) 
                       VALUES (?, ?, ?)"""
        try:
            c = db.cursor()
            query_params = (os.getlogin(), 
                            name, 
                            shell, 
                            '', 
                            False, 
                            stdout, 
                            stderr, 
                            int(time.time()))
            c.execute(insert_query, query_params)
            c.execute("SELECT LAST_INSERT_ROWID()")
            rowid = c.fetchone()[0]
            c.execute("SELECT id FROM job where rowid = ?", (rowid, ))
            job_id = c.fetchone()[0]
            script_fname = os.path.join(self.sjs_root, 'spool', str(job_id))
            open(script_fname, 'w').write(script)
            c.execute("UPDATE job SET script = ? WHERE id = ?", 
                      (script_fname, job_id))
            for (i, arg) in enumerate(script_args):
                c.execute(arg_query, (job_id, i+1, arg))
            c.close()
        except:
            db.rollback()
            raise
        else:
            db.commit()
        db.close()
        self.log('queued job %d (%s)' % (job_id, name))
        return self.get_job(job_id)

    def get_job(self, job_id):
        return _Job(self, job_id)

    def get_all_jobs(self):
        db = sqlite3.connect(os.path.join(self.sjs_root, 'db.sqlite'))
        c = db.cursor()
        c.execute("SELECT id FROM job ORDER BY id")
        job_ids = [ row[0] for row in c ]
        jobs = [ self.get_job(job_id) for job_id in job_ids ]
        return jobs

    def get_queued_jobs(self):
        jobs = []
        for job in self.get_all_jobs():
            if job.error_flag:
                continue
            if job.is_running():
                continue
            jobs.append(job)
        return jobs

    def get_running_jobs(self):
        jobs = []
        for job in self.get_all_jobs():
            if job.is_running():
                jobs.append(job)
        return jobs

    def start_runner(self):
        if os.fork():
            return
        os.setsid()
        os.chdir(os.path.expanduser('~'))
        os.close(0)
        os.close(1)
        os.close(2)
        one = os.open('/dev/null', os.O_RDONLY)
        os.open(os.path.join(self.sjs_root, 'qrun.stdout'), 
                os.O_WRONLY | os.O_APPEND)
        os.open(os.path.join(self.sjs_root, 'qrun.stderr'), 
                os.O_WRONLY | os.O_APPEND)
        self.log('qrunner (%d) started' % os.getpid())
        while True:
            if len(self.get_running_jobs()) >= self.slots:
                self.log('qrunner (%d) all slots filled' % os.getpid())
                break
            jobs = self.get_queued_jobs()
            if not jobs:
                self.log('qrunner (%d) no queued jobs' % os.getpid())
                break
            job = jobs[0]
            try:
                job.run()
            except Exception, data:
                self.log('qrunner (%d) error running job %d' % (os.getpid(), 
                                                                job.id))
                self.log('qrunner (%d) %s' % (os.getpid(), str(data)))
                err_info = traceback.extract_tb(sys.exc_info()[-1])
                self.log('qrunner (%d) %s line %d' % (os.getpid(), 
                                                      err_info[-1][0], 
                                                      err_info[-1][1]))
        self.log('qrunner (%d) done' % os.getpid())
        sys.exit(0)

class _Job:

    def __init__(self, cluster, job_id):
        self.cluster = cluster
        db = sqlite3.connect(os.path.join(cluster.sjs_root, 'db.sqlite'))
        c = db.cursor()
        c.execute("SELECT * FROM job WHERE id = ?", (job_id, ))
        row = c.fetchone()
        if not row:
            raise KeyError('job %d not found' % job_id)
        cols = [ el[0] for el in c.description ]
        row_dict = dict(zip(cols, row))
        self.id = row_dict['id']
        self.user = row_dict['user']
        self.name = row_dict['name']
        self.shell = row_dict['shell']
        self.script = row_dict['script']
        self.error_flag = bool(row_dict['error_flag'])
        self.stdout = row_dict['stdout']
        self.stderr = row_dict['stderr']
        self.pid = row_dict['pid']
        if row_dict['t_submit'] is None:
            self.t_submit = None
        else:
            t_sub = row_dict['t_submit']
            self.t_submit = datetime.datetime.fromtimestamp(t_sub)
        if row_dict['t_start'] is None:
            self.t_start = None
        else:
            self.t_start = datetime.datetime.fromtimestamp(row_dict['t_start'])
        query = """SELECT argument 
                     FROM argument 
                    WHERE job_id = ? 
                    ORDER BY ordinal"""
        c.execute(query, (job_id, ))
        self.args = [ row[0] for row in c.fetchall() ]
        c.close()
        db.close()
        return

    def run(self):
        try:
            args = [self.shell, self.script]
            args.extend(self.args)
            environ = dict(os.environ)
            environ['JOB_ID'] = str(self.id)
            environ['JOB_NAME'] = self.name
            stdin = open('/dev/null')
            stdout_path = string.Template(self.stdout).safe_substitute(environ)
            stderr_path = string.Template(self.stderr).safe_substitute(environ)
            stdout = open(stdout_path, 'w')
            stderr = open(stderr_path, 'w')
            po = subprocess.Popen(args, 
                                  stdin=stdin, 
                                  stdout=stdout, 
                                  stderr=stderr, 
                                  env=environ)
            t = int(time.time())
            db = sqlite3.connect(os.path.join(self.cluster.sjs_root, 
                                              'db.sqlite'))
            try:
                c = db.cursor()
                c.execute("UPDATE job SET pid = ?, t_start = ? WHERE id = ?", 
                          (po.pid, t, self.id))
                c.close()
            except:
                db.rollback()
                raise
            else:
                db.commit()
            db.close()
            self.pid = po.pid
            self.t_start = datetime.datetime.fromtimestamp(t)
        except:
            self.set_error()
            raise
        fmt = 'qrunner (%d) started job %d (PID %d)'
        self.cluster.log(fmt % (os.getpid(), self.id, po.pid))
        po.wait()
        stdin.close()
        stdout.close()
        stderr.close()
        self.clean()
        fmt = 'qrunner (%d) job %d finished'
        self.cluster.log(fmt % (os.getpid(), self.id))
        return

    def set_error(self):
        db = sqlite3.connect(os.path.join(self.cluster.sjs_root, 'db.sqlite'))
        try:
            c = db.cursor()
            c.execute("UPDATE job SET error_flag = ? WHERE id = ?", 
                      (True, self.id))
            c.close()
        except:
            db.rollback()
            raise
        else:
            db.commit()
        db.close()
        self.error_flag = True
        return

    def is_running(self):
        return self.t_start is not None

    def clean(self):
        self.cluster.log('deleting job %d' % self.id)
        os.remove(self.script)
        db = sqlite3.connect(os.path.join(self.cluster.sjs_root, 'db.sqlite'))
        try:
            c = db.cursor()
            c.execute("DELETE FROM job WHERE id = ?", (self.id, ))
            c.close()
        except:
            db.rollback()
            raise
        else:
            db.commit()
        db.close()
        return

    def delete(self):
        if self.is_running():
            self.cluster.log('kill %d to end job %d' % (self.pid, self.id))
            os.kill(self.pid, signal.SIGKILL)
        self.clean()
        return

# eof
