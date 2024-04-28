""" 
Transcript Library for QTPy Broker
(C) 2024 Enchanted Engineering
 """

import json
from timeplus import Zulutime

tx = Zulutime()

def transcribe(ref, prompt, args):
    mark = tx.mark()
    print(f"{mark}: {ref} -> {prompt}")
    if args:
        print("  ", args)

# Constructor
class Scribe:

    def __init__(self, ref):
        self.ref = ref  # list of assigned attributes

    def scribe(self, prompt, args=None):
        transcribe(self.ref, prompt, args)
