from ..stats.meta import to_blocks
from pandas import DataFrame 

MB = 1024*1024
block = 16*MB

before = DataFrame([
    {'offset': 0, 'filename': 'a'},
    {'offset': 1*MB, 'filename': 'a'},
    {'offset': 2*MB, 'filename': 'a'},
    {'offset': 17*MB, 'filename': 'a'},
    {'offset': 20*MB, 'filename': 'a'},
    {'offset': 0*MB, 'filename': 'a'},
    {'offset': 0*MB, 'filename': 'b'},
    {'offset': 0*MB, 'filename': 'a'},
    {'offset': 0*MB, 'filename': 'b'}
])

after = DataFrame([
    {'offset': 0, 'filename': 'a'},
    {'offset': 16*MB, 'filename': 'a'},
    {'offset': 0*MB, 'filename': 'a'},
    {'offset': 0*MB, 'filename': 'b'},
    {'offset': 0*MB, 'filename': 'a'},
    {'offset': 0*MB, 'filename': 'b'}
])


def test_blocks():
    blocks = to_blocks(before)
    assert blocks.compare(after).empty

