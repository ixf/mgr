#!/usr/bin/env python
import argparse
from cat import cat

parser = argparse.ArgumentParser()
parser.add_argument('--dir', type=str, required=True)
parser.add_argument('--repeats', type=int, required=True)
args = parser.parse_args()

path = args.dir
repeats = args.repeats

KB = 1024

from os import listdir
from os.path import isfile, join
from random import choice

files = listdir(path)
files = [f for f in files if isfile(join(path, f))]
to_read = [choice(files) for _ in range(len(files))]

for _ in range(repeats):
    for _file in to_read:
        file = join(path, _file)
        cat(file)

