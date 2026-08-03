# MIT License
"""
Device support for other OneWire devices

* Author(s): CanyonCasa
"""

#__version__ = "0.0.0-auto.0"
#__repo__ = "https://github.com/CanyonCasa/Custom-Node-Red-Nodes"

from onewire import OneWireBus, Device
from onewire_ports import OneWirePort 
from onewire_temps import TemperatureSensor 


class DS2423(Device):
    """Device support for DS2423 OneWire 4kb RAM and counter."""

    # device specific constants...
    CATEGORY = 'counter'
    FAMILY = 0x1D
    DESC = 'DS2423 (0x1D) OneWire 4kb RAM and counter'
    SCRATCHPAD_WR = 0x0F
    SCRATCHPAD_RD = 0xAA
    SCRATCHPADD_COPY = 0x5A
    MEMORY_READ = 0xF0
    MEMORY_READ_AND_COUNTER = 0xA5

    def __init__(self, bus: OneWireBus, address: bytearray, params: dict={}):
        if __class__.FAMILY != address[0]: raise(f"Device {address} not of type {__class__.__name__}")
        super().__init__(bus, address)
        self.CATEGORY = DS2423.CATEGORY
        self.DESC = DS2423.DESC
        self.desc = params.get('desc',DS2423.DESC)

Device.register(DS2423.FAMILY,DS2423)

class DS2438(Device):
    """Device support for DS2438 OneWire Battery Gauge"""

    CATEGORY = 'gauge'
    FAMILY = 0x26
    DESC = 'DS2438 (0x26) Battery Gauge'

    def __init__(self, bus: OneWireBus, address: bytearray, params: dict={}):
        if __class__.FAMILY != address[0]: raise(f"Device {address} not of type {__class__.__name__}")
        super().__init__(bus, address)
        self.CATEGORY = DS2438.CATEGORY
        self.DESC = DS2438.DESC
        self.desc = params.get('desc',DS2438.DESC)

Device.register(DS2438.FAMILY,DS2438)


### DOES NOT SUPPORT CHAIN AND PORT FUNCTIONS AT THIS TIME!
class DS28EA00(TemperatureSensor,OneWirePort):

    # Device specific definitions
    CATEGORY = 'multifunction'
    FAMILY = 0x42
    DESC = 'DS28EA00 (0x42) Chainable Temperature Sensor w/PIO'

    def __init__(self, bus: OneWireBus, address: bytearray, params: dict={}):
        params['desc'] = params.get('desc',DS28EA00.DESC)
        super().__init__(bus, address, params)
        self.CATEGORY = DS28EA00.CATEGORY
        self.DESC = DS28EA00.DESC
        self.desc = params.get('desc',DS28EA00.DESC)

Device.register(DS28EA00.FAMILY, DS28EA00)


# DOES NOT SUPPORT MEMORY FUNCTIONS AT THIS TIME!
class DS28E04(OneWirePort):
    """Device support for DS28E04 4Kb Addressable EEPROM w/PIO"""

    CATEGORY = 'eeprom'
    FAMILY = 0x1C
    DESC = 'DS28E04 (0x1C) 4kb EEPROM w/PIO'
    MASK = 0x7F
    PORT_MASK = 0x03
    PORT_WRITE = 0x5A
    PORT_READ_REG_SEQ = [0xF0,0x21,0x02]  # port type specific sequence

    def __init__(self, bus: OneWireBus, address: bytearray, params: dict):
        if __class__.FAMILY != address[0]: raise(f"Device {address} not of type {__class__.__name__}")
        super().__init__(bus, address)
        self.CATEGORY = DS28E04.CATEGORY
        self.DESC = DS28E04.DESC
        self.desc = params.get('desc',DS28E04.DESC)

Device.register(DS28E04.FAMILY,DS28E04)

