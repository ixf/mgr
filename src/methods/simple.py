from src.fs.operation import Read
from src.env import Env
from .base import Base
from pympler.asizeof import asizeof

class Stride(Base):
    a: Read
    b: Read

    def __init__(self):
        self.a = None
        self.b = None

    def push(self, read):
        self.a = self.b
        self.b = read

    def _predict(self):
        if not self.a:
            return None
        
        if not self.a.filename != self.b.filename:
            return None

        stride = self.a.offset - self.b.offset
        return self.b.replace(
            offset=self.b.offset - stride
        )


class FirstSuccessor(Base):
    def __init__(self):
        self.reads = {}
        self.last_read = None

    def push(self, read):
        if self.last_read not in self.reads:
            self.reads[self.last_read] = read

        self.last_read = read

    def _predict(self):
        got = self.reads.get(self.last_read) or False
        return got

    def memory(self):
        return asizeof(self.reads)


class LastSuccessor(FirstSuccessor):
    def push(self, read):
        self.reads[self.last_read] = read
        self.last_read = read

    def memory(self):
        return asizeof(self.reads)


class StableSuccessor(Base):
    def memory(self):
        return asizeof(self.reads) + asizeof(self.last_read) + asizeof(self.current) + asizeof(self.N)

    def __init__(self, N=2):
        self.reads = {}
        self.current = {}
        self.last_read = None
        self.N = N

    def push(self, read):
        if self.last_read is not None:
            if self.last_read not in self.reads:
                a = [None for _ in range(self.N)]
                a[-1] = read
                self.reads[self.last_read] = a
            else:
                past = self.reads[self.last_read]
                self.reads[self.last_read] = past[1:] + [read]

            successors = self.reads.get(read)
            if successors and all(map(lambda x: x == successors[0], successors)):
                self.current[read] = successors[0]

        self.last_read = read

    def _predict(self):
        if p := self.current.get(self.last_read):
            return p
        return False


class RecentPopularity(Base):
    def memory(self):
        return asizeof(self.reads) + asizeof(self.last_read) + asizeof(self.j) + asizeof(self.N)

    def __init__(self, j=2, k=3):
        self.reads = {}
        self.last_read = None
        self.j = j
        self.N = k

    def push(self, read):
        if self.last_read is not None:
            if self.last_read not in self.reads:
                a = [None for _ in range(self.N)]
                a[-1] = read
                self.reads[self.last_read] = a
            else:
                past = self.reads[self.last_read]
                self.reads[self.last_read] = past[1:] + [read]

        self.last_read = read

    def _predict(self):
        if self.last_read not in self.reads:
            return False
        past = self.reads[self.last_read]
        candidates = past
        while len(candidates) >= self.j:
            e = candidates[-1]
            count = sum(map(lambda x: x == e, past))
            if count >= self.j and e is not None:
                return e
            candidates = list(filter(lambda x: x != e, candidates))
        return False


class FirstStableSuccessor(Base):
    pass
