#!/usr/bin/env python
import argparse
import time

parser = argparse.ArgumentParser()
parser.add_argument('--file', type=str, required=True)
parser.add_argument('--repeats', type=int, default=1)
args = parser.parse_args()

file = args.file
repeats = args.repeats

KB = 1024
bs = 128 * KB

def cat(filename):
    total = 0
    with open(filename, 'r') as f:
        read = True
        while read:
            time.sleep(0.1)
            read = f.read(bs)
            total += len(read)
    return total

def tac(filename, start):
    pos = start - bs
    with open(filename, 'r') as f:
        while pos > 0:
            f.seek(pos)
            f.read(bs)
            time.sleep(0.1)
            pos -= bs


for _ in range(repeats):
    total = cat(file)
    tac(file, total)

