# MIT License
# Custom user defined interface drivers for broker
"""
`custom_drivers.py`
====================================================
Implements instances of various I/O functions for CootiePy

* Author(s): 

Every driver should be defined as a class with the following structure 
    given by the Unicorn example
Note: Capitalize driver class name and append "Driver", for example
    definition { "driver": "Unicorn", "name": "unicorn", "debug": True }
    driver => class UnicornDriver
"""

class UnicornDriver:

    def __init__(self, cfg, verbose=False):
        self.cfg = cfg
        self.verbose = verbose
        self.name = cfg['name']
        self.instances = []
        self.aliases = {}

    def createInstance(self, io, aliases):
        # see other drvier.py examples for necessary actions...
        instance = {}
        self.instances.append(instance)
        for a in aliases:
            exists = self.aliases.get(a)
            if exists:
                scribe(f"WARN: Unicorn instance alias '{a}' exists; redefining alias")
            else:
                if self.verbose: scribe(f"Creating Unicorn instance '{a}' reference")
            self.aliases[a] = len(self.instances) - 1
        return self.instances[len(self.instances) - 1]

    def handler(self, msg):
        index = self.aliases.get(msg['id'])
        if index==None:
            return {'tag': "err", 'err': f"NO defined Unicorn instance: {msg['id']}"}
        instance = self.instances[index]
        # handle message...
        return msg

    def poll(self):
        # must be defined
        pass

    # define other functions as needed by handler and poll
