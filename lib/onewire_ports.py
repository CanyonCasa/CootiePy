# MIT License
"""
Device support for OneWire port (I/O) devices

* Author(s): CanyonCasa
"""

#__version__ = "0.0.0-auto.0"
#__repo__ = "https://github.com/canyoncasa/OneWire.git"

from onewire import OneWireBus, Device


class OneWirePort(Device):

    CATEGORY = 'port'
    PORT_MASK = 0xFF
    PORT_READ = 0xF5
    PORT_READ_REG_SEQ = []  # port type specific sequence 
    PORT_WRITE_REG = 0x5A
    PORT_INTERLEAVE = False


    def __init__(self, bus: OneWireBus, address: bytearray, params: dict):
        super().__init__(bus, address)
    
    # low level port I/O function to retrieve the RAW port pin states (i.e. no inversion handling)
    def portIn(self, raw=False):
        self.select()
        self.bus.write([self.PORT_READ])
        response = self.bus.read(1)
        self.bus.reset()    # required to stop command
        data = response[0]
        if raw:
            return data
        if self.PORT_INTERLEAVE:
            data = ((data & 0x04)>>1) + ((data & 0x01))
        return data & self.PORT_MASK

    def portReadReg(self):
        if self.PORT_INTERLEAVE:
            data = self.portIn(True)
            data = ((data & 0x08)>>2) + ((data & 0x02)>>1)
            return data & self.PORT_MASK
        self.select()
        self.bus.write(self.PORT_READ_REG_SEQ)
        response = self.bus.read(1)
        self.bus.reset()
        print(f"portReadReg: ",response)
        return response[0] & self.PORT_MASK

    # sets the RAW (i.e. no inversion handling) port latch state data
    def portWriteReg(self, data):
        # mask data and fill bits...
        data = (data & self.PORT_MASK) | (~self.PORT_MASK & 0xFF)
        self.select()
        self.bus.write([self.PORT_WRITE_REG,data,data^0xFF])
        response = self.bus.read(2)
        self.bus.reset()    # required to stop command
        print(f"portWriteReg: ",response)
        if not response[0]==0xAA:
            return None
        data = response[1]
        if self.PORT_INTERLEAVE:
            data = ((data & 0x08)>>2) + ((data & 0x02)>>1)
        return data & self.PORT_MASK

    # high-level DS2408, DS2413, or DS28EA00 port operations with error checking...
    # gets or sets port latch or pin data per operation. Assumes...
    #   !!! Assumes inverting logic so that a 1 turns the output ON
    #   wIOIN and wIOREG do not change the port 
    #   wIOSET, wIOCLEAR, and wIOTOGGLE operations preserve bits with 0 value and only change 1 bits
    #   wIORESET, wIOOUT do not preserve bits and write all bits of the port, both 0's and 1's.
    def port(self, op, data=0xFF):
        print(f"op: {op}, data: {data}")
        if type(data)=='str': data = int(data,16) # hex string to decimal
        if op == 'RESET':
            data = self.portWriteReg(self.PORT_MASK)
        elif op == 'CLEAR':
            data = self.portWriteReg(data | self.portReadReg())
        elif op == 'SET':
            data = self.portWriteReg(~data & self.portReadReg())
        elif op == 'IN':
            data = self.portIn()
        elif op == 'REG':
            data = self.portReadReg()
        elif op == 'OUT':
            data = self.portWriteReg(~data)  # inverts?
        elif op == 'TOGGLE':
            data = self.portWriteReg(data ^ self.portReadReg())
        elif op == 'PULSE':
            data = self.portWriteReg(data ^ self.portWriteReg(data ^ self.portReadReg()))
        else:
            return None
        return self.PORT_MASK & ~data

    def action(self, info: dict) -> int:
        """parses input data record into a value and/or action for port call"""
        try:
            op = info.get('op')
            if 'value' in info:     # write directly to port
                op = op or 'OUT'
                value = info['value']
                return { 'op': op,  'operand': value, 'data': self.port(op, value) }
            if 'channel' in info:
                op = op or 'TOGGLE'
                channel = info['channel']
                if str(channel) in {'0','1','2','3','4','5','6','7'}:
                    n = int(channel)
                elif channel in {'a','b','c','d','e','f','g','h'}:
                    n = 'abcdefgh'.index(channel)
                else:
                    return { 'op': 'IN', 'operand': None, 'data': self.portIn() }
                value = 1 << n
                return { 'op': op, 'operand': value, 'data': self.port(op, value) }
            if not op in {'IN','REG'}:
                op = 'IN'
            return { 'op': op, 'operand': None, 'data': self.port(op) }
        except Exception as ex:
            print(f"ERROR[{type(ex).__name__}] in OneWirePort.action", ex.args)
            return { 'info': info, 'ex': type(ex).__name__, 'call': 'OneWirePort.action' }


class DS2408(OneWirePort):
    """Device support for DS2408 8-bit I/O port."""

    # device specific constants...
    FAMILY = 0x29
    DESC = 'DS2408 (0x29) 8-bit I/O port'
    PORT_MASK = 0xFF
    PORT_READ_REG_SEQ = [0xF0,0x89,0x00]  # port type specific sequence 


    def __init__(self, bus: OneWireBus, address: bytearray, params: dict):
        if __class__.FAMILY != address[0]: raise(f"Device {address} not of type {__class__.__name__}")
        self.PORT_MASK = params.get('port_mask',DS2408.PORT_MASK)
        super().__init__(bus, address, params)

Device.register(DS2408.FAMILY,DS2408)


class DS2413(OneWirePort):
    """Device support for DS2413 2-bit I/O port."""

    # device specific constants...
    FAMILY = 0x3A
    DESC = 'DS2413 (0x3A) 2-bit I/O port'
    PORT_MASK = 0x03
    PORT_INTERLEAVE = True

    def __init__(self, bus: OneWireBus, address: bytearray, params: dict):
        if __class__.FAMILY != address[0]: raise(f"Device {address} not of type {__class__.__name__}")
        self.PORT_MASK = params.get('port_mask',DS2413.PORT_MASK)
        super().__init__(bus, address, params)

Device.register(DS2413.FAMILY,DS2413)

# DS28E04 and DS28E04 defined in onewire_other.py
