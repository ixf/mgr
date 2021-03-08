#!/usr/bin/env python
import os

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3' 

import trio
import time
from src.runner import Runner

import logging
log = logging.getLogger('wrun')

all_to_run = [
  'simple1',
  'simple2',
  'simple3',
  'hard1a',
  'hard1b',
  # 'hard2a',
  # 'hard2b',
  'zip',
  'wf1',
  # 'wf2'
]

results_dir = "traces"

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--all', type=bool, default=False)
parser.add_argument('to_run', nargs='*', default=all_to_run)

args = parser.parse_args()
do_skips = args.all
to_run = args.to_run

max_len = max(map(len, to_run)) + 10

async def run_all_programs():
    log.info(f"Starting.")
    for program in to_run:
        target  ='/'.join([results_dir, program])
        if do_skips and all_to_run == to_run:
          if os.path.isfile(target):
            log.info(f"{target} exists, skipping")
            continue

        a = time.time()
        df = await Runner(program).run()
        df.to_csv(target)
        b = time.time()
        s = time.strftime('%Hh %Mm %Ss', time.gmtime(b-a))

        align = max_len - len(program)
        log.info(f"{program}{' ' * align}{s}")

    log.info(f"Done. {len(to_run)} programs ran.")

trio.run(run_all_programs)
