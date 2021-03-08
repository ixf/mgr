#!/usr/bin/env python
# grupy plikow maja wspolne sekwencje odczytow wewnatrz danego pliku (kojarzenie nazwa pliku -> sekwencja)
# np w 1 11 21 sekwencja abcd
#    w 2 12 22 sekwencja dbca
# do porownania:
# m grup o n sekwencjach
# 1 grupa o m*n sekwencjach
# pierwszy przypadek powinien dzialac lepiej jezeli sa kojarzone

import random
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--filedir', type=str, required=True,
                    help='source file directory')
parser.add_argument('--filecount', type=int, required=True,
                    help='total files')
parser.add_argument('--group_count', type=int, required=True)
parser.add_argument('--group_len', type=int, required=True)
parser.add_argument('--seq_count', type=int, required=True)
parser.add_argument('--seq_len', type=int, required=True)
parser.add_argument('--seq_repeats', type=int, required=True)
parser.add_argument('--file_repeats', type=int, required=True)

args = parser.parse_args()

random.seed(1024)
KB = 1024

filedir = args.filedir
filecount = args.filecount
group_count = args.group_count
group_len = args.group_len
seq_count = args.seq_count
seq_len = args.seq_len
seq_repeats = args.seq_repeats
file_repeats = args.file_repeats


# grupy to po prostu 1-10 11-20 itd
groups = list(range(1, filecount+1))
groups = [groups[i:i+group_len] for i in range(group_count)]
id_to_g = lambda id: id // group_len

def shuffled(gen):
    ls = list(gen)
    random.shuffle(ls)
    return ls

for i in range(50):
    groups_seq = [
        [shuffled(range(0, seq_len)) for _ in range(seq_count)]
            for _ in range(group_count)
    ]

    order_within_group = shuffled(range(0, group_len))
    def next_file(g_id):
        while True:
            for g in order_within_group:
                yield g_id * 10 + g + 1

    files_per_group = file_repeats // group_count

    for g_id in range(group_count):
        seqs = groups_seq[g_id]
        file_gen = next_file(g_id)
        for f_repeat in range(files_per_group):
            filename = next(file_gen)
            f = open(filedir + "/" + str(filename))

            for s_repeat in range(seq_repeats):
                some_seq = random.sample(seqs, k=1)[0]
                some_jump = random.randint(0, 30) * 32 * KB

                for el in some_seq:
                    offset = some_jump + el * KB
                    f.seek(offset)
                    f.read(KB)
            f.close()
