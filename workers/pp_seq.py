!/usr/bin/env python
import random
from time import sleep
from sys import argv

KB = 1024
MB = KB*KB

name = argv[1]
scale1 = int(argv[2])
scale2 = int(argv[3])

for i in range(8):
    with open(name, 'r') as file:
        # read first 16KB
        file.read(16*KB)
        sleep(0.01)

        # then do some semisequential reads
        for j in range(scale1):
            random_offset = random.randint(2,16)
            random_offset *= MB

            seq = [random_offset + 16*KB*j for j in range(scale2)]
            # slight shuffle:
            for j in range(int(scale2/2)):
                a = random.randint(0,scale2-1)
                b = random.randint(0,scale2-1)
                seq[a], seq[b] = seq[b], seq[a]

            for j in seq:
                file.seek(j);
                file.read(16*KB)
                sleep(0.005)
