from ..fs.cache import Cache
from ..fs.operation import Read

rs = [
    Read(filename="qwe", offset=0, length=1024),
    Read(filename="qwe", offset=1024, length=1024),
    Read(filename="qwe", offset=4096, length=1024),
    Read(filename="qwe", offset=5*1024, length=1024),
    Read(filename="qwe", offset=7*1024, length=1024),
    Read(filename="qwe", offset=8*1024, length=1024),
    Read(filename="qwe", offset=7*1024, length=1024)
]

def test_1():
    l = Cache(block_size=1024, capacity= 3*1024)
    for r in rs:
        l.put(r)
        l.trim()
    assert [('qwe', 5*1024), ('qwe', 8*1024), ('qwe', 7*1024)] == list(l.lru)

def test_2():
    l = Cache(capacity= 3*1024)
    l.put(rs[0])
    assert l.get(rs[0])

    before = l.space
    l.trim()
    after = l.space
    assert before == 2048 and after == 2048

    l.put(rs[1])
    l.trim()
    l.put(rs[2])
    l.trim()
    l.put(rs[3])

    before = l.space
    assert before == -1024
    l.trim()
    after = l.space
    assert after == 0
