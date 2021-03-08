from dataclasses import dataclass, field, replace
import time
from pandas import Series

@dataclass
class Operation:
    filename: str

    def to_list(self):
        return {}

@dataclass(unsafe_hash=True)
class Read(Operation):
    offset: int
    length: int = field(compare=False,)
    real_length: int = field(init=False, compare=False, default=-1)
    timestamp: float = field(init=False, compare=False,)
    pid: int = field(compare=False, default=-1)
    hit: bool = field(default=False, compare=False,)
    source: str = field(default='read', compare=False,)
    full_read: bool = field(default=False, compare=False,)
    fingerprint: str = field(default='', compare=False,)

    def __post_init__(self):
        self.timestamp = time.time()
        self.real_length = self.length

    def move(self, by):
        nu_length = max(self.length-by, 0)
        return Read(filename=self.filename, offset=self.offset+by, length=nu_length, pid=self.pid, hit=self.hit)
    
    def replace(self, **attrs):
        return replace(self, **attrs)

    @classmethod
    def columns(_cls):
        return {
           'kind': Series([], dtype='str'),
           'filename': Series([], dtype='str'),
           'timestamp': Series([], dtype='float'),
           'offset': Series([], dtype='int'),
           'length': Series([], dtype='int'),
           'real_length': Series([], dtype='int'),
           'hit': Series([], dtype='float'),
           'pid': Series([], dtype='int'),
           'source': Series([], dtype='str'),
           'fingerprint': Series([], dtype='str')
        }

    def to_list(self, tss=0):
        return [
            self.kind(),
            self.filename,
            self.timestamp - tss,
            self.offset,
            self.length,
            self.real_length,
            self.hit,
            self.pid,
            self.source,
            self.fingerprint
        ]

    def kind(self):
        if self.source == 'prefetch':
            return 'Prefetch'
        if self.hit:
            return 'Hit'
        return 'Miss'

def read_from_series(series):
    return Read(offset = series.offset,
        filename = series.filename,
        length = series.length,
        pid = series.pid,
    )


