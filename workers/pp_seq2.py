#!/usr/bin/env python
import random
from time import sleep
from sys import argv

KB = 1024
MB = KB*KB

name = argv[1]
scale1 = int(argv[2])
scale2 = int(argv[3])
scale3 = int(argv[4])

file_size = 50*MB
parts = 32*16

seq_count = scale3
shuffles_count = scale2 // 2
seqs = [
    [16*KB*j for j in range(scale2)]
    for s in range(seq_count)
]

random.seed(0)

for seq in seqs:
    for s in range(shuffles_count):
        a = random.randint(0, scale2-1)
        b = 0
        while b == a:
            b = random.randint(0, scale2-1)
        seq[a], seq[b] = seq[b], seq[a]


for i in range(scale1):
    with open(name, 'r') as file:

        random_offset = file_size * random.randint(0, parts) // parts
        random_sequence = random.choice(seqs)

        for random_read in random_sequence:
            file.seek(random_read + random_offset)
            file.read(16*KB)
            sleep(0.01)

