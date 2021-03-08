#!/usr/bin/env python
from sys import argv
import time

filename = argv[1]
repeats = int(argv[2])
times = int(argv[3])

def basic_reads(name, repeats=3, times=6, nested=None):
    with open(name, 'r') as f:
        for _ in range(repeats):
            for i in range(times):
                time.sleep(0.05)
                f.seek(2*4096*i);
                if nested != None:
                    nested()
                f.read(2)

basic_reads(filename, repeats=repeats, times=times)
