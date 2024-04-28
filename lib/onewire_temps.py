# MIT License
"""
Device support for OneWire temperature sensors

* Author(s): CanyonCasa
"""

#__version__ = "0.0.0-auto.0"
#__repo__ = "https://github.com/canyoncasa/OneWire.git"

from onewire import OneWireBus, Device
from time import sleep

class TemperatureSensor(Device):

    CATEGORY = 'temperature'
    TEMP_CONVERT_WAIT = 800 # ms @ 12 bits
    CONVERT_T = 0x44
    RD_SCRATCH = 0xBE
    WR_SCRATCH = 0x4E
    COPY_SCRATCH = 0x48
    
    def __init__(self, bus: OneWireBus, address: bytearray, params: dict={}):
        super().__init__(bus, address, params)
        bits = params.get('resolution',0)
        self.bits = bits if bits in [9,10,11,12] else 12   # vaildate, default 12
        units = params.get('units','').upper()
        self.units = units if units in ['F','C','K','R','X','-'] else 'F'  # valudate, default F
        self.resolution(self.bits)  # set resolution
        self.wait = TemperatureSensor.TEMP_CONVERT_WAIT >> (12-self.bits)
        self.CATEGORY = TemperatureSensor.CATEGORY

    def scratchpad_copy(self):
        self.select()
        self.bus.write([TemperatureSensor.COPY_SCRATCH])

    def scratchpad_read(self) -> bytearray:
        self.select()
        self.bus.write([TemperatureSensor.RD_SCRATCH])
        sp_and_crc = self.bus.read(9)
        if self.bus.crc8(sp_and_crc):
            return bytearray(8)
        return sp_and_crc[0:8]

    def scratchpad_write(self, buf: bytearray) -> None:
        self.select()
        self.bus.write([TemperatureSensor.WR_SCRATCH])
        self.bus.write(buf)
    
    def temperature(self, units=None, wait=False) -> float:
        # converts raw temperature to specified format
        def temp_as(raw: int, units: str = '') -> float:
            temp = raw if raw<32768 else raw - 65536
            if units == 'C':
                return temp / 16
            elif units == 'F':
                return (temp / 16) * 1.8 + 32
            elif units == 'K':
                return (temp / 16) + 273.15
            elif units == 'R':
                return (temp / 16) * 1.8 + 491.67
            elif units == 'X':
                return "0x{:04X}".format(raw)
            else:
                return { t:temp_as(raw,t) for t in 'CFKRX' }
        # load scratchpad and extract temperature
        def getT(units):
            self.select()
            buf = self.scratchpad_read()
            raw_temp = (buf[1]<<8) + buf[0]
            return temp_as(raw_temp,(units,self.units)[units==None])
        if self.bus.busy:
            if self.bus.ready:  # conversion ready
                return getT(units)
            else:
                return None
        else:   # not busy, so can start conversion
            self.select()
            self.bus.write([TemperatureSensor.CONVERT_T])
            if wait:    # blocking to other functions
                sleep(self.wait)
                return getT(units)
            else:       # non-blocking, but bus not usable until ready
                self.bus.hold(self.wait)
                return None

    # sets a temperature resolution
    def resolution(self, bits: int) -> int:
        self.select()
        sp = self.scratchpad_read()
        cfg = (bits-9) << 5 | 0x1F
        buf = bytearray([sp[2], sp[3], cfg])
        self.scratchpad_write(buf)
        self.scratchpad_copy()
        return bits


class DS18X20(TemperatureSensor):
    # Device specific definitions
    FAMILY = 0x28
    DESC = 'DS18x20 (0x28) Temperature Sensor'

    def __init__(self, bus: OneWireBus, address: bytearray, params: dict={}):
        if __class__.FAMILY != address[0]: raise(f"Device {address} not of type {__class__.__name__}")
        super().__init__(bus, address, params)
        params['desc'] = params.get('desc',DS18X20.DESC)
        self.DESC = DS18X20.DESC
        self.desc = params.get('desc',DS18X20.DESC)

Device.register(DS18X20.FAMILY, DS18X20)
