from collections import OrderedDict
from .operation import Read
from math import isinf, floor

def _key(read: Read, block_size: int):
    return (read.filename, int(floor(read.offset / block_size) * block_size))

class Cache:
    lru: 'OrderedDict[tuple[str, int], Read]'
    capacity: int
    space: int

    def __init__(self, capacity=8192, block_size=1024):
        self.capacity = capacity
        self.block_size = block_size
        self.clear()
        self._trimmed = True
    
    def clear(self):
        self.space = self.capacity
        self.lru = OrderedDict()

    def get(self, read: Read) -> 'tuple[bool, str]':
        key = _key(read, self.block_size)
        if cause := self.lru.get(key):
            return (True, cause.fingerprint)
        return (False, '')

    def put(self, read: Read):
        if read.length == 0:
            return

        if not self._trimmed:
            raise RuntimeError()

        key = _key(read, self.block_size)
        present = key in self.lru
        if not present:
            self.lru[key] = read
            self.space -= read.length
        else:
            self.lru.move_to_end(key)

        self._trimmed = False

    def trim(self):
        if isinf(self.space):
            self._trimmed = True
            return []
        returns = []
        while self.space < 0:
            old_read = self.lru.popitem(last=False)
            self.space += old_read[1].length
            returns.append(old_read)

        self._trimmed = True
        return returns

