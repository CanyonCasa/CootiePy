#import supervisor
#import microcontroller
import board # type: ignore
#import os
#import usb_cdc
#import json
from scribe import Scribe

from onewire import OneWireBus
import onewire_temps, onewire_ports, onewire_other
try:
    import onewire_user # type: ignore
except:
    pass

#### main code ####

# global variables
#serial = usb_cdc.data   # defines the serial I/F instance
scribe = Scribe('MAIN').scribe
cfg = {
    "driver": "OneWire",
    "debug": True,
    "name": "1wire",
    "params": {"pin": "D1"},
    "instance": True
}

scribe("Initialization...")
pin = getattr(board,cfg["params"]["pin"])
oneWire = OneWireBus(pin)
scribe(f"OneWireBus defined for pin: {pin}")
oneWire.status(cfg["debug"])

try:
    found = oneWire.scan()
    scribe(f"Bus scan found {len(found)} devices.")
    if found:
        for f in found:
            if f['family'] in OneWireBus.REGISTERED:
                scribe(f"Found: {OneWireBus.REGISTERED[f['family']].DESC}")
            else:
                scribe(f"Found[{f['sn']}]: unknown type")
            for key, value in f.items():
              scribe(f"  {key}: {value}")
except Exception as ex:
    scribe(f"ERROR[OneWireDriver.init]: {type(ex).__name__} { ex.args}")
    raise ex

scribe("Execution halted!")
