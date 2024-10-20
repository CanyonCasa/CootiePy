import supervisor
import microcontroller
import os
import usb_cdc
from time import sleep
# global variables
serial = usb_cdc.data   # defines the serial I/F instance

i = 0
while i<100:
    i +=1
    print(f"{i:04d}: Hello World!")
    sleep(5)
