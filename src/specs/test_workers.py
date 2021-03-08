import pandas as pd
from ..runner import Runner
from ..env import Env

# import src
# from src.env import Env
# from src.stats.post import *
# from src.predicting import Predictor
# import src.methods

def df2l(df):
    l = list(df.T.to_dict().values())
    for x in l:
        if "pid" in x:
            del x["pid"]
    return l

def is_subset(superset, subset):
    return all(item in superset.items() for item in subset.items())

async def test_cat():
    df = await Runner('test_docker_processes', workers='workers_tests.yml').run()
    assert df.pid[0] != df.pid[1]
    assert (df.filename == './sources/demo/plik').all()
    assert len(df) == 2

async def test_cat_no_blocks():
    e = Env()
    e.block_size = 5
    df = await Runner('test_docker_processes', env=e, workers='workers_tests.yml').run()

    assert len(df) == 4
    assert df.pid[0] == df.pid[1]
    assert df.pid[1] != df.pid[2]
    assert df.pid[2] == df.pid[3]
    assert (df.filename == './sources/demo/plik').all()

async def test_processes():
    df = await Runner('test_processes', workers='workers_tests.yml').run()
    assert len(set(df.pid)) == 5

async def test_sleep():
    e = Env()
    e.block_size = 131072
    df = await Runner('test_sleep', workers='workers_tests.yml', env=e).run()
    l = df2l(df)

    assert is_subset(l[0], {
        'filename': './sources/demo/plik',
        'hit': False,
        'kind': 'Miss',
        'length': 131072,
        'real_length': 5,
        'offset': 0,
        'source': 'read',
        'timestamp': 0.0
    })

    assert is_subset(l[1], {'filename': './sources/demo/plik',
        'hit': True,
        'kind': 'Hit',
        'length': 131072,
        'offset': 0,
        'source': 'read'
    })
    assert l[1]["timestamp"] > 1
