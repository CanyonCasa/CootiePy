# general purpose event queue handler
class Queue:

    def __init__(self):
        self.n = 0      # number of queue pushes
        self.q = []     # queue data

    @property
    def available(self):
        return len(self.q)

    def flush(self, all=False):
        self.q = []
        if all: self.n = 0

    def push(self,item, index=None):
        if isinstance(item, list):
            for i in item: self.push(i)
        else:
            if index==None:
                self.q.append(item)
            else:
                self.q[index] = item
            self.n += 1
            return len(self.q)
        

    def pull(self, i=0):
        if self.available:
            try:
                return self.q.pop(i)
            except:
                pass
        return None

    def queue(self):
        return self.q.copy()
