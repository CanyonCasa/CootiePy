# MIT License
# Interface drivers for broker
"""
`drivers.py`
====================================================
Implements instances of various I/O functions for CootiePy

* Author(s): CanyonCasa
"""

#__version__ = "0.0.0-auto.0"
#__repo__ = "https://github.com/CanyonCasa/Custom-Node-Red-Nodes"

import json
import board
from analogio import AnalogIn, AnalogOut
import digitalio
import pwmio
from simpleq import Queue
from onewire import OneWireBus
import onewire_temps, onewire_ports, onewire_other
try:
    import onewire_user
except:
    pass

from scribe import Scribe
scribe = Scribe('DRVR').scribe

class OneWireDriver:
    """A class to interface a OneWireBus to the QTPy protocol."""

    def __init__(self, cfg, verbose=False):
        self.cfg = cfg
        self.verbose = verbose
        self.params = cfg['params']
        self.name = cfg['name']
        self.q = Queue()
        self.active = None
        self.instances = []
        self.aliases = {}
        if not 'pin' in self.params:
            raise 'OneWireDriver definition requires a pin parameter!'
        self.bus = OneWireBus(getattr(board,self.params['pin']))
        failed = self.bus.status(cfg.get('debug'))
        if failed:
            raise Exception("ERROR: OneWireDriver[{self.name}]: OneWire bus failure")
        else:
            device = self.bus.define_device(None,{})    # default OneWire Device (bus)
            self.instances.append({ 'cfg': {}, 'address': None, 'device': device }) # add bus as intial instance
            if self.cfg.get('debug'):
                try:
                    found = self.bus.scan()
                    scribe(f"Bus scan found {len(found)} devices.")
                    if found:
                        for f in found:
                            if f['family'] in OneWireBus.REGISTERED:
                                scribe(f"Found[{f['sn']}]: {OneWireBus.REGISTERED[f['family']].DESC}")
                            else:
                                scribe(f"Found[{f['sn']}]: unknown type")
                except Exception as ex:
                    scribe(f"ERROR[OneWireDriver.init]: {type(ex).__name__} { ex.args}")
                    raise ex

    def createInstance(self, io, aliases):
        if not 'sn' in io:
            raise 'OneWireDriver instance requires a serial number (sn) parameter!'
        address = OneWireBus.frmt_addr(OneWireBus.bytes4addr(io['sn']))
        device = self.bus.define_device(address['rom'], io.get('params',{}))
        instance = { 'cfg': io, 'address': address, 'device': device }
        #if self.verbose: scribe(f"OneWireDriver instance: {instance}")
        self.instances.append(instance)
        index = len(self.instances) - 1
        alist = []
        for a in aliases:
            exists = self.aliases.get(a)
            if exists:
                scribe(f"WARN: OneWire instance '{address['sn']}' alias '{a}' exists; redefining alias")
            self.aliases[a] = index
            if a!=address['sn']:
                alist.append(a)
        scribe(f"Created OneWire instance[{address['sn']}]: {', '.join(alist)}")
        return self.instances[index]

    def handler(self, msg):
        self.q.push(msg)
        #if self.verbose: scribe(f'handler[{self.name},{self.q.available}]: {msg}')

    def poll(self):
        def packet(data):
            tmp = (type(self.active)(self.active))
            self.active = None
            tmp.update(data)
            return tmp
        # process pending actions...
        if not self.active and self.q.available:
            self.active = self.q.pull()
        if self.active:
            try:
                ref = self.aliases.get(self.active['id'],0)
                instance = self.instances[ref]
                category = self.active.get('CATEGORY',instance['device'].CATEGORY)
                if category=='temperature':
                    units = self.active.get('units',instance['device'].units)
                    temp = instance['device'].temperature(units)
                    if temp==None: return None
                    return packet({'temperature':temp, 'units': units})
                elif category=='port':
                    return packet(instance['device'].action(self.active))
                elif category=='bus':
                    family = self.active.get('family')
                    status = instance['device'].bus.status(self.active.get('dump'))
                    scan = None if status else instance['device'].search(family)
                    existing = {}
                    known = {}
                    unknown = []
                    for i in self.instances:
                        sn = None if not i['address'] else i['address']['sn']
                        if sn:
                            name = i['cfg'].get('name',"unnamed")
                            existing[sn] = name
                    if scan:
                        for x in scan:
                            x['rom'] = str(x['rom'])
                            #if self.verbose: scribe(f"bus scan found: {x['sn']}")
                            k = existing.get(x['sn'],None)
                            if k:
                                known[x['sn']] = k
                            else:
                                unknown += [x['sn']]
                    return packet({'status': status, 'scan': scan, 'known': known, 'unknown': unknown })
            except Exception as ex:
                scribe(f"Error[OneWireDriver.poll: {ex}")
                packet(ex)
                return None

class AnalogDriver:

    def __init__(self, cfg, verbose=False):
        self.cfg = cfg
        self.verbose = verbose
        self.name = cfg['name']
        self.instances = []
        self.aliases = {}

    def createInstance(self, io, aliases):
        params = io.get('params',{})
        if not 'pin' in params:
            raise 'Analog instance requires a pin parameter per instance!'
        name = io.get('name',params['pin'])
        pin = getattr(board,params['pin'])
        instance = {'cfg': io, 'name': name, 'pin':pin, 'range':params.get('range',3.3), 
            'bias':params.get('bias',0.0), 'units':params.get('units'), 'init': params.get('init')}
        if instance['init']==None:
            try:
                instance['input'] = AnalogIn(instance['pin'])
            except:
                scribe(f"WARN: Analog input not supported for {instance['name']}, pin: {instance['pin']}!")
                return None
        else:
            try:
                instance['output'] = AnalogOut(instance['pin'])
            except:
                scribe(f"WARN: Analog output not supported for {instance['name']}, pin: {instance['pin']}!")
                return None
            self.output(instance,instance['init'])
        if self.verbose: scribe(f"AnalogDriver instance: {instance}")
        self.instances.append(instance)
        for a in aliases:
            exists = self.aliases.get(a)
            if exists:
                scribe(f"WARN: Analog instance alias '{a}' exists; redefining alias")
            else:
                if self.verbose: scribe(f"Creating Analog instance '{a}' alias reference")
            self.aliases[a] = len(self.instances) - 1
        return self.instances[len(self.instances) - 1]

    def handler(self, msg):
        index = self.aliases.get(msg['id'])
        if index==None:
            return {'tag': "err", 'err': f"NO defined Analog instance: {msg['id']}"}
        instance = self.instances[index]
        if 'out' in msg:
            result = self.output(instance,msg['out'])
        else:
            result = self.input(instance)
        for k,v in result.items():
            msg[k] = v
        return msg

    def poll(self):
        pass

    def output(self,instance,value):
        if isinstance(value,float):
            out = round((value - instance['bias']) * 65536 / instance['range'])
        else:
            out = int(value)
        if not instance['output']: return {err: f"Output to Analog Input {instance['name']}"}
        instance['output'].value = out
        return {'data': out}
    
    def input(self,instance):
        if not instance['input']: return {err: f"Input from Analog Output {instance['name']}"}
        raw = instance['input'].value
        value = (raw /65536) * instance['range'] + instance['bias']
        return {'raw': raw, 'value': value, 'units': instance['units']}

"""
`DigitalDriver`
====================================================
Implements instances of basic digital I/O
Parameters:
    pin:    I/O pin board name
    init:   Initial value; undefined for input
    term:   Termination, UP or DOWN or OD (open drain) or undefined for push-pull (default)
    out:    Output value or array of values processed on successive polls

    values:
        0:  0, '0', 'L', False
        1:  1, '1', 'H', True
"""

class DigitalDriver:

    def __init__(self, cfg, verbose=False):
        self.cfg = cfg
        self.verbose = verbose
        self.name = cfg['name']
        self.instances = []
        self.aliases = {}
        self.watches = []

    def createInstance(self, io, aliases):
        params = io.get('params',{})
        if not 'pin' in params:
            raise 'Digital instance requires a pin parameter per instance!'
        pin = getattr(board,params['pin'])
        name = io.get('name',params.get('name',pin))

        instance = { 'cfg': io, 'name': name, 'pin': pin, 'init': str(params.get('init','')).upper(),
            'term': params.get('term','').upper(), 'io': None, last: None, tag: str(params.get('tag','')) }
        try:
            instance['io'] = DigitalInOut(instance['pin'])
            if not instance['init']:
                instance['io'].direction = digitalio.Direction.INPUT
                instance['dir'] = 'IN'
                if instance['term']=='UP':
                    instance['io'].pull = digitalio.Pull.UP
                if instance['term']=='DOWN':
                    instance['io'].pull = digitalio.Pull.DOWN
                if params.get('watch',False):
                    self.watches.append(len(self.instances)) # index of this instance (not yet added)
            else:
                instance['io'].direction = digitalio.Direction.OUTPUT
                instance['dir'] = 'OUT'
                if instance['term']=='OD':
                    instance['io'].DriveMode = digitalio.DriveMode.OPEN_DRAIN
                else:
                    instance['io'].DriveMode = digitalio.DriveMode.PUSH_PULL
                instance['io'].value = self.state(instance['init'])
        except:
            mode = ('output','input')[instance['init']==""]
            scribe(f"WARN: Digital {mode} not defined correctly for {instance['name']}, pin: {instance['pin']}!")
            return None
        if self.verbose: scribe(f"DigitalDriver instance: {instance}")
        self.instances.append(instance)
        for a in aliases:
            if self.aliases.get(a): # already exists?
                scribe(f"WARN: Digital instance alias '{a}' exists; redefining alias")
            else:
                if self.verbose: scribe(f"Creating Digital instance '{a}' alias reference")
            self.aliases[a] = len(self.instances) - 1 # instance aliases reference the primary instance
        return self.instances[len(self.instances) - 1]

    def handler(self, msg):
        index = self.aliases.get(msg['id'])
        if index==None:
            return {'tag': "err", 'err': f"NO defined Digital instance: {msg['id']}"}
        instance = self.instances[index]
        if 'out' in msg:
            if hasattr(out, "__length__"):
                instance['out'] = out
                self.watches.append(index)
            else:
                instance['io'].value = self.state(value)
        msg['value'] = instance['io'].value
        return msg

    def poll(self):
        msgs = []
        for w in self.watches[:]:
            instance = self.instances[w]
            if instance['dir']=='OUT':
                instance['io'].value = instance['out'][0]
                instance['last'] = instance['out'][0]
                instance['out'] = instance['out'][1:]
                if len(instance['out'])==0:
                    del self.watches[w]
            else:
                msg = { 'id': instance['name'], 'old': instance['last'], 'new': instance['value'] }
                instance['last'] = msg['new']
                if instance['tag']:
                    msg.tag = instance['tag']
                msgs.append(msg)
        return msgs

    def state(self, v):
        if v in [0,'0','L',False]: return False
        if v in [1,'1','H',True]: return True
        return None

"""
`PWMDriver`
====================================================
Implements instances of PWMIO
Parameters:
    pin:    I/O pin board name
    freq:   Nominal output Frequncy, default 100
    dc:     Duty cycle, 0-65535 / 65535 or 0-100% if scale is set, default 0
    var:    Variable frequency mode, default False
    scale:  Value for scaling duty cycle as a percent, default 0
    offset: Value to offset duty cycle, enables a minimum duty cycle, default 0

    if scale == 0:
        PWM = dc/65353
    else:
        PWM = offset + math.floor(dc*scale/100)
"""
class PWMDriver:

    def __init__(self, cfg, verbose=False):
        self.cfg = cfg
        self.verbose = verbose
        self.name = cfg['name']
        self.instances = []
        self.aliases = {}

    def createInstance(self, io, aliases):
        
        params = io.get('params',{})
        if not 'pin' in params:
            raise 'PWM instance requires a pin parameter per instance!'
        name = io.get('name',params['pin'])
        pin = getattr(board,params['pin'])
        instance = { 'cfg': io, 'name': name, 'pin':pin, 'dc':params.get('dc',0),
            'freq': params.get('freq',100), 'offset': params.get('offset',0),
            'scale': params.get('scale',0), 'var': params.get('var',False) }
        try:
            instance['pwm'] = pwmio.PWMOut( instance['pin'], 
                self.calc_dc(instance['dc'],instance['scale'],instance['offset']),
                instance['freq'], instance['var'] )
        except:
            scribe(f"WARN: PWM not supported for {instance['name']}, pin: {instance['pin']}!")
            return None
        if self.verbose: scribe(f"PWMDriver instance: {instance}")
        self.instances.append(instance)
        for a in aliases:
            exists = self.aliases.get(a)
            if exists:
                scribe(f"WARN: PWM instance alias '{a}' exists; redefining alias")
            else:
                if self.verbose: scribe(f"Creating PWM instance '{a}' reference")
            self.aliases[a] = len(self.instances) - 1
        return self.instances[len(self.instances) - 1]

    def handler(self, msg):
        index = self.aliases.get(msg['id'])
        if index==None:
            return {'tag': "err", 'err': f"NO defined PWM instance: {msg['id']}"}
        instance = self.instances[index]
        if 'dc' in msg:
            instance['PWM'].duty_cycle = self.calc_dc(msg['dc'],instance['scale'],instance['offset'])
        if instance['var'] and 'freq' in msg:
            instance['pwm'].frequency = msg['freq']
        
        return msg

    def poll(self):
        pass

    def calc_dc(self, dc, scale, offset):
        if scale==0:
            return dc
        else:
            return offset + math.floor(dc * (scale-offset) / 100)
