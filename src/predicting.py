from .methods import *

klasses = {
    # test
    'none': Noop,
    # basic
    'stride': Stride,
    'fs': FirstSuccessor,
    'ls': LastSuccessor,
    'ss': StableSuccessor,
    'rp': RecentPopularity,
    # first method
    'dtc': Dtc,
    # second
    'lstm': Lstm2,
}

def make_predictor(method: 'Base | str | None') -> Base:
    if isinstance(method, Base):
        return method
    elif isinstance(method, str):
        return klasses[method]()
    elif method == None:
        return klasses['none']()
    else:
        raise RuntimeError()

