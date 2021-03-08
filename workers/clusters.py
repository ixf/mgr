import random
from typing import List
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--file', type=str, required=True,
                    help='source file')

args = parser.parse_args()
filename = args.file

KB=1024
MB=1024*KB
spaces = 5
size = 2*MB

sequence_len = 32
sequence_count = 4

def shuffled(gen) -> List[int]:
    ls = list(gen)
    random.shuffle(ls)
    return ls

starts = [size * i * 5 for i in range(spaces)]
sp_sequences = [ 
    [shuffled(range(sequence_len)) for _ in range(sequence_count)]
    for _ in range(spaces)
]


with open(filename) as f:
    # select some space
    for n in range(30):
        space = random.randint(0, spaces-1)
        sequences = sp_sequences[space]
        start = starts[space]

        # make some sequences specific to it
        for x in range(30):
            seq_offset = start + random.randint(0, 16) * 64 * KB
            seq = random.choice(sequences)
            for o in seq:
                f.seek(seq_offset + o * 8 * KB)
                f.read(8*KB)
