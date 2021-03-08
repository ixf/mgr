import faulthandler
from src.fs.operation import Read
faulthandler.enable()

from pandas import DataFrame

from os.path import getsize

from .cache import Cache
from ..env import Env
from .fingerprint import fingerprint

class Cachedict:
    """cache wrapper for a funciton"""

    def __init__(self, f):
        self.f = f
        self.d = {}

    def __getitem__(self, key):
        if key not in self.d:
            self.d[key] = self.f(key)
        return self.d[key]

    def __setitem__(self, key, value):
        self.d.__setitem__(key, value)

    def __delitem__(self, key):
        self.d.__delattr__(key)


def safe_getsize(f):
    try:
        return getsize(f)
    except FileNotFoundError:
        return 1024


# its only task is to save reads with correct `hit` values (based on cache)
# inputs include predictions (made by a predictor, not from a dataframe)
# timestamps dont matter
class MockFuse():
    cache: Cache
    ops: 'list[dict]'
    env: Env

    def __init__(self, columns, env: Env):
        self.ops = []
        # used for cache capacity
        self.env = env
        self.cache = Cache(capacity=env.cache_capacity, block_size=env.block_size)
        self.file_sizes = Cachedict(safe_getsize)
        self.columns = columns

    def read(self, op, prefetched=False):
        if prefetched:
            op.source = 'prefetch'
            if op.full_read:
                self.full_read(op)
                return
        (hit, fp) = self.cache.get(op)
        op.hit = hit

        if prefetched:
            op.fingerprint = fingerprint()
        if hit and not prefetched:
            op.fingerprint = fp

        self.cache.put(op)
        self.cache.trim()
        self.ops.append(op.to_list())

    def make_df(self):
        df = DataFrame(self.ops, columns=self.columns)
        tss = df.timestamp.min()
        df.timestamp -= tss
        return df
    
    def full_read(self, op: Read):
        org = op
        size_left = self.file_sizes[op.filename]
        bs = self.env.block_size
        position = 0
        while size_left > 0:
            op = op.replace(full_read=False, length=bs, offset=position)
            if org.offset != op.offset:
                self.read(op, prefetched=True)
            position += bs
            size_left -= bs
