# MIT License
# Derived from Adafruit CircuitPython OneWireIO library
"""
`emulate1wIO`
====================================================
Emulates the low level OneWire IO routines for testing search algorithm, etc.

* Author(s): CanyonCasa
"""

#__version__ = "0.0.0-auto.0"
#__repo__ = "https://github.com/CanyonCasa/Custom-Node-Red-Nodes"

# from microcontroller import Pin

def hex2bits(h):
    return bin(int(h,16)).replace('0b','0000000')[-8:]

class OneWire:
    """A class to represent low-level 1-Wire IO."""
    SEARCH_ROM = 0xF0
    MODE_UNDEF = 0
    MODE_CMD = 1
    MODE_MATCH = 2
    MODE_SEARCH = 3

    def __init__(self, pin) -> None:
        self.pin = pin
        self.bit = 0
        self.mode = self.MODE_UNDEF
        self.cmd = 0
        self.search = {'state': True, 't':None, 'c':None}
        self.devices = []

    def init(self, addresses: list) -> dict:
        for sn in addresses:
            bits = ''
            sn = sn.replace(' ','')
            pairs = [sn[i:i+2] for i in range(0,len(sn),2)]
            for p in pairs:
                bits = hex2bits(p) + bits
            self.devices.append({'sn':sn, 'bits': bits[::-1], 'active': False })

    def deinit() -> None:
        pass

    def __enter___():
        return self

    def __exit() -> None:
        pass

    def reset(self) -> bool:
        self.bit = 0
        self.cmd = 0
        self.mode = self.MODE_CMD
        for d in self.devices:
            d["active"] = True
        return len(self.devices)==0

    def read_bit(self) -> bool:
        if self.mode==self.MODE_CMD:
            self.write_bit(True)
            return True
        elif self.mode==self.MODE_SEARCH:
            if self.search['state']==True:
                self.__seek()
                return self.search['t']
            elif self.search['state']==False:
                self.search['state'] = None
                return self.search['c']
            else:
                print('error: search expecting a write value' )
                return None

    def __seek(self):
        t = 1
        c = 1
        for d in self.devices:
            if d['active']:
                t = t & int(d['bits'][self.bit])
                c = c & (1-int(d['bits'][self.bit]))
        self.search = {'state':False, 't': t, 'c': c}

    def write_bit(self, value: bool) -> None:
        if self.mode==self.MODE_CMD:
            self.cmd += value<<self.bit
            self.bit += 1
            if self.bit==8:
                self.bit = 0
                if self.cmd==self.SEARCH_ROM:
                    self.mode = self.MODE_SEARCH
                    self.search = {'state': True, 't':None, 'c':None}
                    self.bit = 0
                    print('searching...')
        elif self.mode==self.MODE_SEARCH and self.search['state']==None:
            for d in self.devices:
                if d['active']:
                    if not int(d['bits'][self.bit])==value:
                        d['active'] = False
                        print(f"clash[{self.bit}({value},{d['bits'][self.bit]})]: {d['sn']}")
                    else:
                        #print(f"match[{self.bit}({d['bits'][self.bit]})]: {d['sn']} ({d['bits']})")
                        pass
            self.bit += 1
            self.search['state'] = True
            return None
        else:
            print('not ready')