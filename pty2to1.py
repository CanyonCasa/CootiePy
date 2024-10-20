#! /usr/bin/python

# interfaces a hardware serial port to a pair of pseudoterminals

# SYNTAX: pty2to1.py <hardware_port> [<pseudo_link_prefix>} [<hardware params>]

# EXAMPLE:  pty2to1.py /dev/ttyACM0 ptty
#   will create two pseudoterminals in /dev/pts, where # is defined by the OS
#   the script will create symbolic links or each to /dev/ptty0 and /dev/ptty1
#   input from /dev/ttyACM0 is sent to both ptty0 and ptty1
#   data recieved from either ptty0 or ptty1 is sent to /dev/ttyACM0

# data flow is assumed to be line formated

import sys
import os
import serial

# get commandline agrguments...
if len(sysargv)<2:
    print("SYNTAX: pty2to1.py <hardware_port> [<pseudo_link_prefix>,default:ptty] [<hardware params>,default 115200,8N1")
    exit()

port = argv[1]
ptty = 'ptty' if len(sys.argv)<3 else sys.argv[2]
params = '115200,8N1' if len(sys.argv)<4 else sys.argv[3]
(baud,frmt) = params.split(',')
(bits,parity,stop) = [*frmt]

# create psuedoterminals
(master0,slave0) = os.openpty()
(master1,slave1) = os.openpty()
# create reference links
os.symlink(os.ttyname(slave0),ptty+'0')
os.symlink(os.ttyname(slave1),ptty+'1')

# open and configure serial port
sp = serial.Serial(port)
sp.baudrate = int(baud)
sp.parity = parity
sp.stopbits = int(stop)
sp.open()

# pass data...
buf0 = ''
buf1 = ''
while sp.is_open:
    while sp.in_waiting:
        line = sp.readline()
        os.write(master0,line)
        os.write(master1,line)
    line0 = ''
    while True:
        data0 = os.read(slave0,1024)
	if data0:
            buf0 = buf0 + data0
            while True
                pos0 = buf0.find('\n') + 1
                if not pos0:
                    break
                line0 = buf0[0:pos0]
                buf0 = buf[pos0:]
                sp.write(line0)
        else:
            break
    while True:
        data1 = os.read(slave1,1024)
	if data1:
            buf1 = buf1 + data1
            while True
                pos1 = buf1.find('\n') + 1
                if not pos1:
                    break
                line1 = buf1[0:pos1]
                buf1 = buf[pos1:]
                sp.write(line1)
        else:
            break

# cleanup
sp.close()
os.unlink(ptty+'0')
os.unlink(ptty+'1')
os.close(slave0)
os.close(slave1)
