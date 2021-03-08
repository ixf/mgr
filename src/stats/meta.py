from pandas import DataFrame 

# converts reads of addresses to reads on full blocks
# (rounds down to e.g. full 16MB and ignores consecutive reads in the same block)
# for one pid

class BlockConverter:
    def __init__(self, columns, blocksize):
        self.last_read = None
        self.arr = []
        self.nu = DataFrame(columns=columns)
        self.block = blocksize

    def feed(self, read):
        this_block = read.offset // self.block

        if self.last_read is not None and \
            this_block == self.last_read.offset // self.block and \
            read.filename == self.last_read.filename:
            return
        else:
            # new block
            this_read = read.copy()
            this_read.offset = this_block * self.block
            self.arr.append(this_read)
            self.last_read = this_read

            self.last_read.length = self.block
            self.last_read.end = self.last_read.offset + self.last_read.length

    def get_all(self):
        self.nu = self.nu.append(self.arr)
        return self.nu
        

def to_blocks(df, blocksize=1024*1024*16):
    bc = BlockConverter(df.columns, blocksize)
    for _, read in df.iterrows():
        bc.feed(read)
    nu = bc.get_all()
    return nu.reset_index(drop=True)

def consecutive_reads_by_pid(df):
    seq = list(df.pid)
    last = None
    count = 0
    counts = []
    for item in seq:
        if item != last:
            counts.append([last, count])
            count = 1
            last = item
        else:
            count += 1
        
    counts.append([last, count])
    return counts

def count_reads_by_pid(df, column='pid'):
    return df[column].value_counts()

