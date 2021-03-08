from zipfile import ZipFile
import random
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--repeats', type=int, required=True)
parser.add_argument('--dir', type=str, required=True)

args = parser.parse_args()
repeats = args.repeats
d = args.dir

small = [
  ["small", str(i)] for i in range(1,33)
]
zipped = [
  ["zip", i] for i in range(1, 65)
]
random.shuffle(zipped)
zipped = zipped[0:8]

all_elements = small + zipped
random.shuffle(all_elements)

chunked = [
  [random.choice(all_elements) for _ in range(256)]
  for _ in range(32)
]

def cat(f, block_size=8*1024):
  got = True
  while got:
    b = f.read(block_size)
    got = len(b) > 0

def read_zip(i):
  with ZipFile(f"{d}/large.zip") as z:
    fn = z.infolist()[i-1]
    with z.open(fn.filename) as f:
      cat(f)


def read_file(i):
  with open(f"{d}/small/{i}") as f:
    cat(f)

# ileś razy wybierz sekwencje i zrób ready
for repeat_i in range(repeats):
  sequence = random.choice(chunked)
  for (kind, i) in sequence:
    if kind == "zip":
      read_zip(i)
    elif kind == "small":
      read_file(i)
    else:
      raise RuntimeError()
