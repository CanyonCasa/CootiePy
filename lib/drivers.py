# MIT License
# Interface drivers for broker
"""
`onewire`
====================================================
Wrapper for a OneWireBus to queue and process messages

* Author(s): CanyonCasa
"""

#__version__ = "0.0.0-auto.0"
#__repo__ = "https://github.com/canyoncasa/OneWire.git"

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
            print(f"ERROR: OneWireDriver[{self.name}] bus error")
        else:
            if self.cfg.get('debug'):
                found = self.bus.scan()
                for f in found:
                    print(f"Found[{f[2]}]: {OneWireBus.REGISTERED[f[0]].DESC}")

    def createInstance(self, io, aliases):
        if not 'sn' in io:
            raise 'OneWireDriver instance requires a serial number (sn) parameter!'
        address = OneWireBus.frmt_addr(OneWireBus.bytes4addr(io['sn']))
        device = self.bus.define_device(address['rom'], io.get('params',{}))
        instance = { 'cfg': io, 'address': address, 'device': device }
        if self.verbose: print(f"OneWireDriver instance: {instance}")
        self.instances.append(instance)
        for a in aliases:
            exists = self.aliases.get(a)
            if exists:
                print(f"WARN: OneWire instance '{address['sn']}' alias '{a}' exists; redefining alias")
            else:
                if self.verbose: print(f"Creating OneWire instance '{address['sn']}' alias '{a}' reference")
            self.aliases[a] = len(self.instances) - 1
        return self.instances[len(self.instances) - 1]

    def handler(self, msg):
        self.q.push(msg)
        if self.verbose: print(f'handler[{self.name},{self.q.avaliable()}]: {msg}')

    def poll(self):
        def packet(data):
            tmp = (type(self.active)(self.active))
            self.active = None
            tmp.update(data)
            return tmp
        # process pending actions...
        if not self.active and self.q.available:
            self.active = self.q.pull()
            #print(f"active: {self.active}")
        if self.active:
            instance = self.instances[self.aliases[self.active['id']]]
            action = self.active.get('action',instance['device'].TYPE)
            #print(f"ACTIVE INSTANCE: {instance}")
            #print(f"action: {action}")
            if action=='temperature':
                units = self.active.get('units',instance['device'].units)
                temp = instance['device'].temperature(units)
                if temp==None: return None
                return packet({'temperature':temp, 'units': units})
            # if busy, return None
            if self.bus.busy:
                print("busy...")
                return None
            else:
                print("not busy...")
                if action=='bus':
                    status = instance['device'].bus.status()
                    scan = instance['device'].bus.scan()
                    #tmp = type(self.active)(self.active).update({'temperature':temp})
                    return packet({'status': status, 'scan': scan})
                pass
        #return any msgs
        pass

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
                print(f"WARN: Analog input not supported for {instance['name']}, pin: {instance['pin']}!")
                return None
        else:
            try:
                instance['output'] = AnalogOut(instance['pin'])
            except:
                print(f"WARN: Analog output not supported for {instance['name']}, pin: {instance['pin']}!")
                return None
            self.output(instance,instance['init'])
        if self.verbose: print(f"AnalogDriver instance: {instance}")
        self.instances.append(instance)
        for a in aliases:
            exists = self.aliases.get(a)
            if exists:
                print(f"WARN: Analog instance alias '{a}' exists; redefining alias")
            else:
                if self.verbose: print(f"Creating Analog instance '{a}' reference")
            self.aliases[a] = len(self.instances) - 1
        return self.instances[len(self.instances) - 1]

    def handler(self, msg):
        index = self.aliases.get(msg['id'])
        print(f"{index}: {self.aliases}")
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

class DigitalDriver:

    def __init__(self, cfg, verbose=False):
        self.cfg = cfg
        self.verbose = verbose
        self.name = cfg['name']
        self.instances = []
        self.aliases = {}

    def createInstance(self, io, aliases):
        params = io.get('params',{})
        if not 'pin' in params:
            raise 'Digital instance requires a pin parameter per instance!'
        name = io.get('name',params['pin'])
        pin = getattr(board,params['pin'])
        instance = {'cfg': io, 'name': name, 'pin':pin, 'term':params.get('term',"").upper(),
            'init': str(params.get('init','Z')).upper(), 'io': None}
        try:
            instance['io'] = DigitalInOut(instance['pin'])
            if instance['init']=="Z":
                instance['io'].direction = digitalio.Direction.INPUT
                instance['io'].pull = None
                if instance['term']=="UP": instance['io'].pull = digitalio.Pull.UP
                if instance['term']=="DOWN": instance['io'].pull = digitalio.Pull.DOWN
            else:
                instance['io'].direction = digitalio.Direction.OUTPUT
                instance['io'].value = bool(int(instance['init']))
                instance['io'].DriveMode = digitalio.DriveMode.PUSH_PULL
                if instance['term']=="OD": instance['io'].DriveMode = digitalio.DriveMode.OPEN_DRAIN
        except:
            mode = ('output','input')[instance['init']=="Z"]
            print(f"WARN: Digital {mode} not supported for {instance['name']}, pin: {instance['pin']}!")
            return None
        if self.verbose: print(f"DigitalDriver instance: {instance}")
        self.instances.append(instance)
        for a in aliases:
            exists = self.aliases.get(a)
            if exists:
                print(f"WARN: Digital instance alias '{a}' exists; redefining alias")
            else:
                if self.verbose: print(f"Creating Digital instance '{a}' reference")
            self.aliases[a] = len(self.instances) - 1
        return self.instances[len(self.instances) - 1]

    def handler(self, msg):
        index = self.aliases.get(msg['id'])
        print(f"{index}: {self.aliases}")
        if index==None:
            return {'tag': "err", 'err': f"NO defined Digital instance: {msg['id']}"}
        instance = self.instances[index]
        if 'out' in msg: instance['io'].value = bool(int(msg['out']))
        msg['value'] = instance['io'].value
        return msg

    def poll(self):
        pass

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
        instance = {'cfg': io, 'name': name, 'pin':pin, 'dc':params.get('dc',0),
            'freq': params.get('freq',100)}
        try:
            instance['pwm'] = pwmio.PWMOut(instance['pin'])
            instance['pwm'].duty_cycle = self.dutycycle(instance['dc'])
            instance['pwm'].frequency = instance['freq']
        except:
            print(f"WARN: PWM not supported for {instance['name']}, pin: {instance['pin']}!")
            return None
        if self.verbose: print(f"PWMDriver instance: {instance}")
        self.instances.append(instance)
        for a in aliases:
            exists = self.aliases.get(a)
            if exists:
                print(f"WARN: PWM instance alias '{a}' exists; redefining alias")
            else:
                if self.verbose: print(f"Creating PWM instance '{a}' reference")
            self.aliases[a] = len(self.instances) - 1
        return self.instances[len(self.instances) - 1]

    def handler(self, msg):
        index = self.aliases.get(msg['id'])
        print(f"{index}: {self.aliases}")
        if index==None:
            return {'tag': "err", 'err': f"NO defined PWM instance: {msg['id']}"}
        instance = self.instances[index]
        if 'dc' in msg: instance['pwm'].duty_cycle = self.dutycycle(msg['dc'])
        if 'freq' in msg: instance['pwm'].frequency = msg['freq']
        
        return msg

    def poll(self):
        pass

    def dutycycle(self,dc):
        return int(2**16 * dc / 100)