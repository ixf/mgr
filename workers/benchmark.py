#!/usr/bin/env python
from sys import argv
import time

filename = argv[1]


filename = 'big_file'
KB = 1024

def read_until_end(name):
    got = 0
    with open(name, 'r') as f:
        last = f.read(16 * KB)
        got += 16*KB
        while last:
            got += 16*KB
            last = f.read(16 * KB)
    return got

if True:
    start = time.time()
    got = 0
    for i in range(1):
        got += read_until_end(filename)
    end = time.time()
    diff = end-start
    print(f"Total time: #{diff}")
    print(f"Rate: MBps: #{got / 1024 / 1024 / diff}")

