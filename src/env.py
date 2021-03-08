import yaml
import errno
import os

multipliers = {
    "K": 1024,
    "M": 1024*1024,
    "G": 1024*1024*1024,
}

def parse_size(size: str) -> int:
    letter = size[-1]
    if multiplier := multipliers[letter]:
        number = int(size[:-1])
        return number * multiplier
    else:
        return int(size)

def size_to_human(size: float) -> str:
    if size < 1024:
        return f"{size}"
    size = size / 1024.0

    if size < 1024:
        return f"{size:.1f}K"
    size = size / 1024.0

    return f"{size:.1f}M"


class Env:
    cache_capacity: int
    block_size: int
    ping: int

    def __init__(self, name="default"):
        with open('envs.yaml') as f:
            datas = yaml.load(f, Loader=yaml.SafeLoader)
        self.data = datas[name]

        self.ping = self.data.get('ping', 0)
        self.cache_capacity = parse_size(self.data['cache'])
        self.block_size = parse_size(self.data['block_size'])

        self.predictor = None

        is_vagrant = os.getlogin() == 'vagrant'
        if is_vagrant:
            self._ensure_exists('/target')
            os.system('ls -s /target ./target')
        else:
            self._ensure_exists('./target')

    def _ensure_exists(self, d):
        try:
            os.makedirs(d)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

    def source(self):
        return f"./sources/{self.data['source']}"

