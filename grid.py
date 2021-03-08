#!/usr/bin/env python
from src.mock_runner import MockRunner
from src.env import Env
from src.stats import *
import pandas as pd
pd.set_option('display.max_rows', 250)
pd.set_option('display.max_colwidth', 500)

KB = 1024

import os
os.environ["TF_FORCE_GPU_ALLOW_GROWTH"]="true"

grid = Grid()
# grid.workers = ['simple3', 'hard1a', 'hard1b', 'zip']
# grid.methods = ['none', 'dtc', 'ls', 'fs', 'ss']
grid.workers = ['wf1']
grid.methods = ['lstm', 'dtc', 'ls', 'fs', 'ss', 'none']

def measure(name: str, df: DataFrame, predictor: Base, env: Env):
    runner = MockRunner(df, predictor=predictor, env=env)
    try:
        mock_df = runner.run(progress_prefix=name)

        resources = predictor.resources_used()

        mock_df.reindex()

        mock_df.to_csv('mock_df')

        stats = predictor_stats(mock_df)
        return { **stats, **resources }
    except:
        print(f"{name} returned an error for {env.source}")
        return None

grid.measure = measure
print(grid.run())
