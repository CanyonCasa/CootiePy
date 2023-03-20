import rtc
import time as timex
from simpleq import Queue

# singleton class to handle UTC (Zulu time) vs localtime; can be used in place of time class
# tobj = {"epoch":<epoch>, "zone": ["zone_string",<utc_offset>], "dst": 0|1}
class Zulutime:

    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super(Zulutime, cls).__new__(cls)
        return cls.instance

    def __init__(self, tobj=None):
        self.zone = 'UTC'    # default values only, override with settime
        self.offset = 0
        self.adjust = 0
        self.dst = 0
        if tobj:
            self.settime(tobj)

    def settime(self,tobj):
        if not tobj: return None
        if isinstance(tobj,int):
            epoch = tobj//1000  # assume (node-red) time in ms; integer division to preserve resolution 
        if isinstance(tobj, dict):
            (self.zone, self.offset) = tobj.get('zone',[self.zone,self.offset])
            self.adjust = self.offset*3600
            self.dst = tobj.get('dst',self.dst)
            epoch = tobj.get('epoch',timex.time())
        # initialize RTC with "local time" to be consistent with existing time class
        rtc.RTC().datetime = timex.localtime(epoch+self.adjust)

    @property
    def epoch(self):
        return timex.time() - self.adjust

    def utctime(self,secs=None):
        if secs==None:
            secs = self.epoch # set to zulu time
        zt = timex.localtime(secs)[0:8] + (0,)
        return zt

    def iso(self, secs=None):
        utc = self.utctime(secs)
        ustr = "{0}-{1:02d}-{2:02d}T{3:02d}:{4:02d}:{5:02d}.000Z"
        return ustr.format(*utc)

    def local(self, secs=None):
        lt = self.localtime(secs)
        lstr = "{0}-{1:02d}-{2:02d}T{3:02d}:{4:02d}:{5:02d}.000{z} (GMT{ofs:+}:00)"
        return lstr.format(*lt,z=self.zone,ofs=self.offset)

    def datetime(self,secs=None):
        yr, mn, day, h, m, s, wd, yd, dst = self.localtime(secs)
        hr = ((h,h-12)[h>12],h+12)[h==0]
        a = ('AM','PM')[h>11]
        return {
            'date': "{0}-{1:02d}-{2:02d}".format(yr,mn,day),
            'time': "{0}:{1:02d}:{2:02d} {3}".format(hr,m,s,a),
            'short': "{0}/{1} {2}:{3:02d} {4}".format(mn,day,hr,m,a)
        }

    @property
    def timeAs(self):
        epoch = self.epoch
        local = self.local(epoch+self.adjust)
        dt = self.datetime(epoch+self.adjust)
        iso = self.iso(epoch)
        return { 'epoch':epoch, 'local':local, 'iso':iso, 'datetime': dt,
            'zone':self.zone, 'offset': self.offset, 'adj':self.adjust, 'dst':self.dst }

    # other time class wrappers...
    def localtime(self, secs=None):
        lt = timex.localtime(secs)
        lt = lt[0:8] + ((self.dst,) if lt[8]==-1 else (lt[8],))
        return lt

    def time(self):
        return timex.time()

    def monotonic(self):
        return timex.monotonic()

    def sleep(self,secs):
        return timex.sleep(secs)

    def struct_time(self,time_tuple):
        return timex.struct_time(time_tuple)

    def mktime(self,time_tuple):
        return timex.mktime(time_tuple)

"""
simple Linux-like cron server...
jobs defined as dictionaries, where ...
  id: defines a unique reference; if job 'id' exists, any new job replaces the existing job.
  at: cron-like local time string specifying when the job runs; 
      posting an ID without an 'at' spec removes that job.
      spec: <ticks> <min> <hr> <day> <month> <dayOfWeek>
        where ticks = seconds//tick, default tick=10, meaning 10s intervals
        fields support wildcard (*), comma delimited lists, modulo (*/n), and range (-), but not cron keywords
  evt: event (i.e. any valid command or I/O action) to post on trigger
  n:  optional maximum number of times to run job, default infinite
"""
class Cron:

    jobs = Queue()

    def __init__(self, clock, tick=10):
        self.jobs = Cron.jobs
        self.clock = clock
        self.tick = tick
        self.lastcheck = ()

    def job(self, j=None):
        if isinstance(j, list):
            for jx in j: self.job(jx)
        else:
            if j:
                id = j.get('id',None)
                at = j.get('at',None)
                if at:
                    # if defined, parse 'at' field into resolved list for later use; list input left unchanged
                    if type(at)==str: at = at.split(' ')                    # string to list
                    if type(at)==list:                                      # check list fields for list, range, and modulo
                        for i,f in enumerate(at):
                            if ',' in f: at[i] = ['list',f.split(',')]      # sublist for list
                            if '-' in f: at[i] = ['range',[int(x) for x in f.split('-')]]  # sublist of range [start,end]
                            if '/' in f: at[i] = ['mod',int(f.split('/',1)[1])] # list entry for modulo
                            if type(f)==str and f.isdigit(): at[i] = int(f)
                    j['_at_'] = at    # save parsed-at, but preserve original at string
                if id:
                    found = False
                    for i,jj in enumerate(self.jobs.q):
                        if jj.get('id','')==id:
                            found = True
                            if at:
                                self.jobs.push(j,i) # replace job in queue
                                break
                            else:
                                self.jobs.pull(i)   # remove job without at
                                break
                    if at and not found:
                        self.jobs.push(j)           # add to job queue
        return self.jobs.q.copy()
    
    def time(self,tsecs=None):  # returns cron time fields
        if tsecs==None:
            tsecs = self.clock.time()
        (mn,d,h,m,s,wd) = self.clock.localtime(tsecs)[1:7]
        fields = (s//self.tick,m,h,d,mn,(wd+1)%7)
        return fields

    def check(self, tsecs=None):    # check each job for activity
        ct_fields = self.time(tsecs)
        if ct_fields == self.lastcheck: return []
        self.lastcheck = ct_fields
        triggered = []
        for k,j in enumerate(self.jobs.q):
            n = j.get('n',True)
            if n and int(n)>0:   # not defined (default to True) or a number > 0
                match = True
                jt = j['_at_']
                for i,f in enumerate(jt):
                    t = ct_fields[i]
                    if f=='*': continue
                    if type(f)==list:
                        if f[0]=='list' and (t in f[1]): continue
                        if f[0]=='range' and (t in range(f[1][0],f[1][1])): continue
                        if f[0]=='mod' and not (t % f[1]): continue
                    if t==f: continue
                    match = False
                    break
                if match:
                    triggered.append(j.get('evt',None))
                    if not n==True:
                        self.jobs.q[k].n = int(n)-1
        return triggered

