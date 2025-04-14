""" 
Library for QTPy Broker
(C) 2022 Enchanted Engineering
 """

import sys
import json
import board
# from nvstore import NVStore
from timeplus import Zulutime, Cron
from simpleq import Queue
from drivers import *

from scribe import Scribe
scribe = Scribe('BRKR').scribe

# Configuration/Definition class object for simpler dot notation references
class Definition:

    def __init__(self, obj={}):
        self._keys_ = []        # list of assigned attributes
        self.add(obj)

    def has(self, key=None):
        if key == None:
            return self._keys_.copy()
        return hasattr(self, key)

    def add(self, obj={}):
        if isinstance(obj, list):
            for a in obj:
                self.add(a)
        else:
            for k in obj.keys():
                setattr(self,k,obj[k])
                if not self._keys_.count(k):
                    self._keys_.append(k)
    
    def remove(self, key=None):
        if key==None:
            for k in self._keys_:
                self.remove(k)
        else:
            if hasattr(self, key):
                delattr(self, key)
                self._keys_.remove(k)
    
    def resolve(self, key=None, default=None):
        if key==None:
            dx = {}
            for k in self._keys_:
                dx[k] = getattr(self,k)
            return dx
        if not self.has(key):
            self.add(dict([(key, default)]))
        return getattr(self,key)


# singleton class for managing io endpoints...
class IO:

    def __new__(cls, obj=None, verbose=False):
        if not hasattr(cls, 'instance'):
            cls.instance = super(IO, cls).__new__(cls)
        return cls.instance

    def __init__(self, obj=None, verbose=False):
        self.verbose = verbose
        self.interfaces = {}
        self.instances = {}
        if obj:
            self.add([d for i,d in enumerate(obj) if 'driver' in d])
            self.add([x for i,x in enumerate(obj) if 'interface' in x])

    def add(self,obj):
        if isinstance(obj, list):
            for o in obj:
                self.add(o)
        else:
            if 'driver' in obj:
                driver = obj['driver']
                name = obj.get('name','unknown')
                verbose = obj.get('debug',self.verbose)
                try:
                    if name=='unknown':
                        raise ValueError(f"No driver name defined for {driver}")
                    if self.verbose:
                        scribe(f"Adding driver: {name}")
                    if driver in ['OneWire','Analog','Digital','PWM']: 
                        dx = getattr(__import__('drivers'),driver+'Driver')
                    else:
                        dx = getattr(__import__('custom_drivers'),driver+'Driver')
                    if dx==None:
                        scribe(f"WARN: Unknown driver[{driver}]: {name} --> {obj}")
                    else:
                        scribe(f"{driver}[{name}]: {dir(dx)}")
                        self.interfaces[name] = dx(obj, verbose)
                        scribe(f"Driver[{driver}] {name} defined!")
                        inst = obj.get('instance',False)
                        if inst:
                            self.instances[name] = name
                            scribe(f"Driver[{driver}] {name} 'self' instance added!")
                except Exception as ex:
                    scribe(f"ERROR[{type(ex).__name__}]: IO.add Failed to load driver: {name} --> {driver} {ex.args}")
                    raise ex
            elif 'interface' in obj:
                try:
                    aliases = [str(x) for x in (set([obj.get('id'),obj.get('name'),obj.get('sn'),obj.get('addr')] +
                        obj.get('aliases',[])) - {None})]   # aliases defined for each io object for cross references
                    if self.verbose: scribe(f"Adding instance[{obj['interface']}]: {aliases}")
                    interface = self.interfaces.get(obj['interface'],None)
                    if not interface:
                        scribe(f"WARN: Ignoring instance {self.identity(obj)}, interface {obj['interface']} NOT DEFINED")
                    else:
                        interface.createInstance(obj, aliases)
                        for a in aliases:
                            exists = self.instances.get(a)
                            if exists:
                                scribe(f"WARN: Interface '{obj['interface']}' alias '{a}' exists; redefining alias")
                            else:
                                if self.verbose: scribe(f"Creating instance alias '{a}' for interface '{obj['interface']}'")
                            self.instances[a] = obj['interface']
                except Exception as ex:
                    scribe(f"ERROR[{type(ex).__name__}]: IO.add Failed to load instance", ex.args)
                    raise ex
            else:
                scribe("WARN: I/O definition lacks driver/interface property", obj)

    def handle(self, msg, trace=False):
        instance = self.instances.get(msg['id'])
        interface = self.interfaces.get(instance)
        if trace:
            scribe(f"handler[{msg['id']}]: {instance}:{interface.name}")
        try:
            #if self.verbose: scribe(f"IO.handle: id->{msg['id']}, instance->{instance}, interface->{interface}")
            return interface.handler(msg)
        except Exception as ex:
            scribe(f"ERROR[{type(ex).__name__}]: broker[IO.handle]: {instance}, {interface}")
            return None

    def identity(self, cfg):
        return str(cfg.get('id',cfg.get('name',cfg.get('sn',cfg.get('addr','UNKNOWN')))))

    def poll(self,trace=False):
        results = []
        for interface in self.interfaces.values():
            result = interface.poll()
            if result: 
                results.append(result)
                if trace:
                    scribe(f"poll[{interface.name}]")
        return results


# singleton class holding all global shared broker Data ...
class Glob:

    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super(Glob, cls).__new__(cls)
        return cls.instance

    def __init__(self):
        # shared data
        self.utc = Zulutime()       # universal time object
        self.errors = Definition()  # Error logging object
        self.cfg = Definition()     # dot object to hold configuration parameters
        self.io = IO()              # management of io endpoints
        self.cron = Cron(self.utc)  # management of cronjobs
        self.msgs = Queue()         # incoming message queue
        self.rtn = Queue()          # return message queue
        #self.actions = Queue()      # action message queue
        self.events = Queue()       # cronjob events

    # report error...
    def error(self,e=None):
        if e==None:
            ex = {} 
            for k in self.errors.has():
                ex[k] = self.errors.resolve(k,None)
            return ex
        self.errors.add(dict([(e, self.errors.resolve(e,0)+1)]))
            