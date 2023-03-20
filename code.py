import supervisor
import microcontroller
import os
import usb_cdc
import json
from broker import Glob, IO # custom broker library

# global variables
serial = usb_cdc.data   # defines the serial I/F instance
glob = Glob()           # broker global data instance for easy dot notation access.
loopInterrupt = False   # loop interrupt hook
exit = False            # exit hook flag

def load_definition(glob,file=None):
    if file == None:
        file = 'def.json'
    try:
        d = open(file,'rt').read()
        def_obj = json.loads(d)
        if 'cfg' in def_obj:
            glob.cfg.remove()
            glob.cfg.add(def_obj['cfg'])
        verbose = glob.cfg.resolve('verbose',False)
        if verbose: print('load_definition: configuration processed')
        if 'io' in def_obj:
            glob.io = IO(def_obj['io'],verbose)
        if verbose: print('load_definition: i/o processed')
        if 'jobs' in def_obj:
            glob.cron.jobs.flush(True)
            glob.cron.job(def_obj['jobs'])
        if verbose: print('load_definition: (cron) jobs processed')
        print(f"Definition file '{file}' successfully loaded")
        return file
    except Exception as ex:
        print(f"ERROR[{type(ex).__name__}]: Loading definition file: {file}", ex.args)
        return None

# this method processes serial input, line-by-line, as JSON and places valid msgs in the msgs queue ...
def check_for_messages(serial, glob):
    quiet = glob.cfg.resolve('quiet',False)
    cfg_ack = glob.cfg.resolve('ack',False)
    # only if input is available...
    while serial.in_waiting:
        # read binary buffer input by line, remove \n, convert to string
        line = serial.readline().strip().decode('utf8')
        if line:    # ignore empty lines
            # assume input is JSON and convert to dictionary (i.e. Python object)
            try:
                msg = json.loads(line)
                msg['err'] = None   # add an error field to return
                glob.msgs.push(msg)
                if not quiet:
                    # acknowledge message if requested, per msg (precedence) or globally
                    ack = msg.get('ack',cfg_ack)
                    if ack == 'echo':
                        msg({ack:'echo'})
                        glob.rtn.push(msg)
                    elif ack=='log':
                        print('ack:',msg)
                    elif ack:
                        mtype = (('unknown','action')['id' in msg],'command')['cmd' in msg]
                        ref = msg.get('tag',msg.get('id',msg.get('cmd','-?-')))
                        glob.rtn.push({'tag': 'ack', 'ack': mtype, 'ref': ref, 'err': None})   # receipt!
            except Exception as e:
                print(f'ERROR[{type(e)}]: {line}\n  {e}')
                if not quiet:
                    glob.rtn.push({'tag': 'err', 'err': e, 'line': line})

# send return msgs...
def return_results(serial,glob):
    while glob.rtn.available:
        msg = glob.rtn.pull()
        serial.write((json.dumps(msg)+'\n').encode('utf8'))

# gather up status info...
def generate_status(glob,prompt=''):
    if prompt: 
        print(f"generate_status[{glob.utc.iso()}]: {prompt}")
    c = glob.cfg.resolve()
    j = [x['id'] for x in glob.cron.job()]
    q = { 'msgs':{'done':glob.msgs.n, 'pending':glob.msgs.available}, 'rtn':{'done':glob.rtn.n, 'pending':glob.rtn.available} }
    status = { 'state': 'ready', 'errors': glob.error(), 'queued': q, 'cfg': c, 'jobs': j }
    if prompt:
        print(status)
        status['prompt'] = prompt
    return status

# check if any cronjobs trigger
def check_cronjobs(glob):
    evts = glob.cron.check()
    if evts:
        glob.events.push(evts)

# runs recieved commands immediately
def execute_command(msg, glob):
    cmd = msg.get('cmd', None)
    rtnMsg = {'tag': msg.get('tag','cmd'), 'cmd': cmd}
    if cmd=='def':
        if 'def' in msg:
            rtnMsg['def'] = load_definition(glob,msg['def'])
        elif 'cfg' in msg:
            glob.cfg.add(msg['cfg'])
            rtnMsg['cfg'] = glob.cfg.resolve()
        elif 'io' in msg:
            glob.io.add(msg['io'])
            rtnMsg['io'] = glob.io.io
        elif 'jobs' in msg:
            glob.cron.job(msg.get('cron',None))
            rtnMsg['jobs'] = glob.cron.jobs.queue()
        else:   # return definition
            rtnMsg['def'] = {'cfg': glob.cfg.resolve(),'jobs':glob.cron.jobs.queue(), 'io': glob.io.io}
    elif cmd=='status':
        rtnMsg['stats'] = generate_status(glob,msg.get('prompt',''))
    elif cmd=='cron':
        rtnMsg['cron'] = glob.cron.job(msg.get('cron',None))
    elif cmd=='time':
        t = msg.get('time',None)
        if t:
            glob.utc.settime(t)
        t = glob.utc.timeAs # capture time so all output values are consistent
        t['sync'] = "sync@"+t['datetime']['short']
        t['tick'] = glob.cron.time(t['epoch'])[0]
        if msg.get('ack')=='log': print("Time set:", t['local'])
        rtnMsg['time'] = t
    elif cmd=='ctrl':
        globals()['loopInterrupt'] = msg.get('ctrl','')
        rtnMsg['state'] = globals()['loopInterrupt']
    elif cmd=='info':
        rtnMsg['info'] = {'os': os.uname(), 'time': glob.utc.timeAs}
    else:
        if not glob.cfg.quiet:
            rtnMsg['err'] = "Unrecognized command!"
            rtmMsg['msg'] = msg
    glob.rtn.push(rtnMsg)

# sorts out input messages and events into commands and actions...
def sift_messages_and_events(glob):
    for src in [glob.msgs, glob.events]:
        while src.available:
            msg = src.pull()
            # is it a command message? if so process in-situ
            if msg.get('cmd',None):
                execute_command(msg, glob)
            # is it an action message, if so queue action
            elif msg.get('id',None):
                action = glob.io.handle(msg)
                if action:
                    glob.rtn.push(action)
            # otherwise unknown
            else:
                if not glob.cfg.quiet:
                    msg['err'] = "Unrecognized message!"
                    glob.rtn.push(msg)

def process_pending_actions(glob):
    results = glob.io.poll()
    if results:
        glob.rtn.push(results)


#### main code ####
print("Initialization...")
if not load_definition(glob): raise RuntimeError("Initialization failed!")
print("Initialization complete!")
    
print("Begin main loop...")
while not exit:
    check_for_messages(serial, glob)
    check_cronjobs(glob)
    sift_messages_and_events(glob)
    process_pending_actions(glob)
    return_results(serial, glob)
    if loopInterrupt:
        if loopInterrupt=='reload':
            print('Executing reload...')
            supervisor.reload()
        if loopInterrupt=='reset':
            print('Commanded reset...')
            glob.utc.sleep(2)
            microcontroller.reset()
        exit = (loopInterrupt=='exit')
    glob.utc.sleep(0.1)

print("Execution halted!")
