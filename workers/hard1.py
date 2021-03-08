#!/usr/bin/env python
import argparse
from random import shuffle, choice
from cat import cat

parser = argparse.ArgumentParser()
parser.add_argument('--dir', type=str, required=True)
parser.add_argument('--repeats', type=int, required=True)
args = parser.parse_args()

path = args.dir
repeats = args.repeats

KB = 1024

def get_files():
    from os import listdir
    from os.path import isfile, join
    from sys import getsizeof
    from random import shuffle
    from operator import itemgetter

    files = listdir(path)
    files = [join(path, x) for x in files]
    sizes = { f: getsizeof(f) for f in files }
    big = max(sizes.items(), key=itemgetter(1))[0]

    files = [f for f in files if isfile(f)]
    files.remove(big)
    shuffle(files)

    return big, files

big, smalls = get_files()

big_parts: 'list[tuple[str, int | str]]' = [
    ('big', offset) for offset in range(255)
]
small_parts: 'list[tuple[str, int | str]]' = [
    ('small', file) for file in smalls
]
parts_to_read = big_parts + small_parts

to_read = [choice(parts_to_read) for _ in range(len(parts_to_read))]

for _ in range(repeats):
    shuffle(parts_to_read)
    with open(big, 'r') as big_file:
        for (kind, part) in parts_to_read:
            if kind == 'big' and type(part) is int:
                big_file.seek(part*16*KB)
                big_file.read(16*KB)
            elif kind == 'small' and type(part) is str:
                cat(part)
            else:
                raise RuntimeError()

