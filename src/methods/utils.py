from typing import Any
from pandas import DataFrame
from src.env import Env
from sklearn.decomposition import TruncatedSVD
import numpy as np
from sklearn.feature_extraction.text import CountVectorizer
from string import ascii_lowercase
from keras.preprocessing.text import Tokenizer

vocab = "/.1234567890" + ascii_lowercase

def get_filenames_to_fully_prefetch(df: DataFrame, env: Env):
    cache = env.cache_capacity
    max_offsets = df.groupby(['filename'])['offset'].max()

    def is_tmp(f: str):
        return f.endswith('.tmp') or f.endswith('.log')

    def is_soykb_output(f: str):
        return 'gatk-output' in f or '20180321' in f

    def is_big_enough(f: str):
        return max_offsets[f] < cache

    # def was_read_linearly

    def should_prefetch(f: str):
        return not is_tmp(f) and not is_soykb_output(f) and is_big_enough(f)

    fs = set(df.filename)
    return {fn: 1.0 if should_prefetch(fn) else 0.0 for fn in fs}


def filename_embedding(filenames: 'list[str]', components=2) -> 'tuple[CountVectorizer, DataFrame]':
    if len(filenames) == 1:
        # otherwise fit_transform causes issues
        filenames = [filenames[0], filenames[0][:-1] + "_"]

    # "bag of chars"
    cv = CountVectorizer(analyzer='char', vocabulary=vocab)
    x = cv.fit_transform(filenames)

    svd = TruncatedSVD(n_components=components)
    x_svd: Any = svd.fit_transform(x)
    dfn = DataFrame()
    dfn["filename"] = filenames
    for xn in range(components):
        dfn["x" + str(xn)] = x_svd[:, xn]
    dfn = dfn.set_index('filename')
    return cv, dfn


def to_boc(filenames: 'np.ndarray'):
    # filenames is ndarray(dtype=string)
    cv = CountVectorizer(analyzer='char', vocabulary=vocab)

    filename_set = list(set(filenames.flatten()))
    tok = Tokenizer()
    tok.fit_on_texts(filename_set)

    return np.array(list(map(lambda series: cv.transform(series).toarray(), filenames)))


def char_tokenizer():
    tok = Tokenizer(char_level=True)
    tok.fit_on_texts([vocab])
    return tok

