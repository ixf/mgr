#!/usr/bin/env python
import random
import argparse
from os.path import join

parser = argparse.ArgumentParser()
parser.add_argument('--filedir', type=str, required=True,
                    help='source file directory')
parser.add_argument('--filecount', type=int, required=True,
                    help='total files')
parser.add_argument('--fileseq_count', type=int, required=True)
parser.add_argument('--fileseq_len', type=int, required=True)
parser.add_argument('--seq_count', type=int, required=True)
parser.add_argument('--seq_len', type=int, required=True)
parser.add_argument('--repeats', type=int, required=True)

args = parser.parse_args()

random.seed(1024)
KB = 1024

filedir = args.filedir
filecount = args.filecount
fileseq_count = args.fileseq_count
fileseq_len = args.fileseq_len
seq_count = args.seq_count
seq_len = args.seq_len
repeats = args.repeats


def shuffled(gen):
    ls = list(gen)
    random.shuffle(ls)
    return ls

fileseq = [
    shuffled(range(1, filecount))[0:fileseq_len]
    for _ in range(fileseq_count)
]

seq = [
    shuffled(range(seq_len))
    for _ in range(seq_count)
]



for i in range(repeats):
    some_fileseq = random.sample(fileseq, k=1)[0]

    for fint in some_fileseq:
        fn = join(filedir, str(fint))
        some_seq = random.sample(seq, k=1)[0]
        
        with open(fn) as f:
            for addr in some_seq:
                f.seek(8*KB*addr)
                f.read(8*KB)
