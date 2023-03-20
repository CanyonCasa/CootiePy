
"""
NVM wrapper to store and recall python dictionaries as JSON, with cycles recordkeeping
    header:
        1 byte              version
        1 byte              header size (16)
        4 bytes             number of write cycles
        4 bytes             data length
        6 bytes             reserved
    nvm:
        size-header_size    data
"""

from microcontroller import nvm

VERSION = 1
INDEX = 16
CYCLES = 2
LENGTH = 6

class NVStore:

    VERSION = 1

    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super(Flash, cls).__new__(cls)
        return cls.instance

    def __init__(self):
        pass

    # available memory size
    @Property
    def size(self):
        if nvm: return len(nvm)
        return None

    def parseheader(self):
        h = nvm[0:INDEX],'little'
        v = h[0]
        c = int.from_bytes(h[CYCLES:CYCLES+4],'little')
        if c==4294967295: c = 0
        dl = int.from_bytes(h[LENGTH:LENGTH+4],'little')
        if dl==4294967295: return 0
        return (v, c, dl)

    def makeheader(self, datalength, cycles):
        v,c,n = self.parseheader()
        header = VERSION.to_bytes(1,'little') + INDEX.to_bytes(1,'little') + \
                (c+1).to_bytes(4,'little') + datalength.to_bytes(4,'little') + (0).to_bytes(INDEX-10,'little')
        return header
        
    # does not erase cycles count by default  
    def erase(self, n=None, index=INDEX):
        s = self.size
        if n==None or n>s or n<0: n = s-index
        nvm[4:n+index] = bytes([255]*n-index)
    
    def recall(self, n=None):
        try:
            if n==None: # read json data
                v,c,n = self.parseheader()
                if n:
                    jx = nvm[INDEX:n+INDEX]
                    return json.loads(jx)
                return None
            else:       # read raw data
                if n>self.size or n<0:
                    n = self.size
                return nvm[0:n]
        except:
            return None

    def store(self, data, index=0):
        if not isinstance(data,bytes):
            bx = json.dumps(data).encode('utf8')
            nb = len(bx)
            if nb > (self.size-INDEX): return None
            header = makeheader(bx)
            nvm[0:nb+INDEX] = header + bx
            return nb
        else:
            # already a bytearray, but check max length and index
            if index<0: index = 0
            if (len(data)+index)>self.size: return None
            nvm[index:len(data)+index] = data
            return len(data)
