# MIT License
"""
Device support for OneWire port (I/O) devices

* Author(s): CanyonCasa
"""

#__version__ = "0.0.0-auto.0"
#__repo__ = "https://github.com/canyoncasa/OneWire.git"

from onewire import OneWireBus, Device


class OneWirePort(Device):

    (CAR,CAW,RPR,RAL,PAW) = ('F5','5A','F0','C3','A5')
    PIO_READ = 0xF5
    PIO_WRITE = 0x5A
    

    



    def __init__(self, bus: OneWireBus, address: bytearray, params: dict):
        super().__init__(bus, address)
    
    # low level port I/O function to retrieve the RAW (i.e. no inversion handling) port pin states
    def portIn(self, sn):
        self.scribe("# call:portIn(%s)" % (sn))
        family = self.getFamily(sn)
        mask = 0xFF if family == DS2408 else 0x03
        sequence = oneWire.CAR + ' FF'
        self.rst()
        response = hexsplit(self.send(' '.join((oneWire.MATCHROM,sn,sequence))),2)
        self.rst()
        checkOK = self.crc(self.maskSN(''.join(response[1:9])))==0
        data = mask # default
        if checkOK:
            data = int(response[-1],16)
            if family in (DS2413,DS28EA00):
                # DS2413 and DS28EA00 latch and port pin bits interleaved
                data = ((data & 0x04)>>1) + ((data & 0x01))
        else:
            self.scribe("# error:portIn")
            return 0xFFFF
        return data & mask
    # retrieves RAW (i.e. no inversion handling) latched port state data
    def portReadReg(self, sn):
        self.scribe("# call:portReadReg(%s)" % (sn))
        family = self.getFamily(sn)
        mask = 0xFF if family == DS2408 else 0x03
        if family == DS2408:
            sequence = oneWire.RPR + ' 89 00 FF'
        elif family == DS28E04:
            sequence = oneWire.RPR + ' 21 02 FF'
        elif family in (DS2413,DS28EA00):
            sequence = oneWire.CAR + ' FF'
        else:
            return None
        self.rst()
        response = hexsplit(self.send(' '.join((oneWire.MATCHROM,sn,sequence))),2)
        self.rst()
        checkOK = self.crc(self.maskSN(''.join(response[1:9])))==0
        data = mask # default
        if checkOK:
            data = int(response[-1],16)
            if family in (DS2413,DS28EA00):
                # DS2413 and DS28EA00 latch and port pin bits interleaved
                data = ((data & 0x08)>>2) + ((data & 0x02)>>1)
        else:
            self.scribe("# error:portReadReg")
            return 0xFFFF
        return data & mask

    # sets the RAW (i.e. no inversion handling) port latch state data
    def portWriteReg(self, sn, data):
        self.scribe("# call:portWriteReg(%s,0x%02X)" % (sn,data))
        family = self.getFamily(sn)
        mask = 0xFF if family == DS2408 else 0x03
        if type(data)=='str': data = int(data,16) # hex string to decimal
        # mask data and fill bits
        data = (data & mask) | (~mask & 0xFF)
        # write instruction different for DS28EA00
        sequence = oneWire.PAW if family == DS28EA00 else oneWire.CAW
        sequence += ' %02X %02X FF FF' % (data,data^0xFF)
        self.rst()
        response = hexsplit(self.send(' '.join((oneWire.MATCHROM,sn,sequence))),2)
        self.rst()
        checkOK = self.crc(self.maskSN(''.join(response[1:9])))==0
        if checkOK and (response[-2] == 'AA'):    # valid response.
            data = int(response[-1],16)
            if family in (DS2413,DS28EA00):
                # DS2413 and DS28EA00 latch and port pin bits interleaved
                data = ((data & 0x08)>>2) + ((data & 0x02)>>1)
        else:
            self.scribe("# error:portWriteReg")
            return 0xFFFF
        return data & mask

    # high-level DS2408, DS2413, or DS28EA00 port operations with error checking...
    # gets or sets port latch or pin data per operation. Assumes...
    #   !!! resolves inverting logic operation so that a 1 turns the output ON
    #   wIOIN and wIOREG do not change the port 
    #   wIOSET, wIOCLEAR, and wIOTOGGLE operations preserve bits with 0 value and only change 1 bits
    #   wIORESET, wIOOUT do not preserve bits and write all bits of the port, both 0's and 1's.
    def port(self, sn, op, data=0xFF):
        self.scribe("# call:port(%s,%s,0x%02X)" % (sn,op,data))
        family = self.getFamily(sn)
        if family in (DS2408, DS2413, DS28EA00, DS28E04):
            REGMASK = 0xFF if family == DS2408 else 0x03
            if type(data)=='str': data = int(data,16) # hex string to decimal
            if op == wIORESET:
                data = self.portWriteReg(sn,REGMASK)
            elif op == wIOCLEAR:
                data = self.portWriteReg(sn, data | self.portReadReg(sn))
            elif op == wIOSET:
                data = self.portWriteReg(sn, ~data & self.portReadReg(sn))
            elif op == wIOIN:
                data = self.portIn(sn)
            elif op == wIOREG:
                data = self.portReadReg(sn)
            elif op == wIOOUT:
                data = self.portWriteReg(sn, ~data)  ##inverts?
            elif op == wIOTOGGLE:
                data = self.portWriteReg(sn, data  ^ self.portReadReg(sn))
            elif op == wIOPULSE:
                data = self.portWriteReg(sn, data ^ self.portWriteReg(sn, data  ^ self.portReadReg(sn)))
            else:
                self.scribe("# call:port => UNKNOWN port operation[" + sn + "]: " + str(op))
                return None
            return REGMASK & ~data
        else:
            self.scribe("# call:port => UNKNOWN port device: " + sn)
            return None


class DS2408(OneWirePort):
    """Device support for DS2408 8-bit I/O port."""

    # device specific constants...
    TYPE = 'port'
    FAMILY = 0x29
    DESC = 'DS2408 (0x29) 8-bit I/O port'

    def __init__(self, bus: OneWireBus, address: bytearray, params: dict):
        if __class__.FAMILY != address[0]: raise(f"Device {address} not of type {__class__.__name__}")
        self.mask = params.get('mask',0xFF)
        self.invert = params.get('invert',0x00)
        super().__init__(bus, address, params)

Device.register(DS2408.FAMILY,DS2408)

class DS2413(OneWirePort):
    """Device support for DS2413 2-bit I/O port."""

    # device specific constants...
    FAMILY = 0x3A
    DESC = 'DS2413 (0x3A) 2-bit I/O port'

    def __init__(self, bus: OneWireBus, address: bytearray, params: dict):
        if __class__.FAMILY != address[0]: raise(f"Device {address} not of type {__class__.__name__}")
        self.mask = params.get('mask',0x02)
        self.invert = params.get('invert',0x00)
        super().__init__(bus, address, params)

Device.register(DS2413.FAMILY,DS2413)
