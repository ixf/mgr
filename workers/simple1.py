#!/usr/bin/env python
import argparse
from cat import cat

parser = argparse.ArgumentParser()
parser.add_argument('--file', type=str, required=True)
parser.add_argument('--repeats', type=int, default=1)
args = parser.parse_args()

file = args.file
repeats = args.repeats

KB = 1024

for _ in range(repeats):
    cat(file)
