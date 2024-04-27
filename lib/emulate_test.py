# import board
from emulate1wIO import OneWire
from emulate1w import OneWireBus
#import onewire_temps, onewire_ports, onewire_other
#try:
#    import onewire_user
#except:
#    pass

addresses = [
    "28 69 2F 2C 0C 32 20 9A",
    "29 EE D2 02 00 00 00 C3",
    "29 0B B7 19 00 00 00 6E",
    "29 E5 D2 02 00 00 00 3B",
    "29 F1 D2 02 00 00 00 BC",
    "28 9E A0 16 A8 01 3C B4"
    ]

#one= OneWire(1)
#print(one.devices)
#one.init(addresses)
#print(one.devices)

#one.reset()
#print(one.devices)
#print(dir(one))
#print(one.init)
#print(hasattr(one,'add'))

#def writebyte(value: int) -> None:
#    for i in range(8):
#        bit = (value >> i) & 0x1
#        one.write_bit(bit)

#writebyte(0xF0)

#for b in range(64):
#    t = one.read_bit()
#    c = one.read_bit()
#    result = t if not (t==c) else 'conflict'
#    one.write_bit(t)
#    print("%i: %i/%i ==> %s" % (b,t,c,result))

print("addresses...")
for d in addresses:
    print(d)

bus = OneWireBus('D1')
bus.io.init(addresses)
devices = bus.scan()
for d in devices:
    print(d['sn'])
print()
devices = bus.scan(0x29)
for d in devices:
    print(d['sn'])
print()
devices = bus.scan(0x28)
for d in devices:
    print(d['sn'])
