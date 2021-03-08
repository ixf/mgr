KB = 1024
def cat(filename, bs=16*KB):
    with open(filename, 'r') as f:
        read = True
        while read:
            read = f.read(bs)

