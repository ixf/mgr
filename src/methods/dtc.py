# decision tree classifier,
# aby decydować czy dany plik powinien być czytany w całości
# (po wykonaniu pierwszgo odczytu)

from src.env import Env
from sklearn.tree import DecisionTreeClassifier
from pympler.asizeof import asizeof
from ..fs.operation import Read
from pandas import DataFrame
from .base import LearningBase
from .utils import filename_embedding, get_filenames_to_fully_prefetch


class Dtc(LearningBase):
    df: DataFrame
    embedded_filenames: 'dict[str, dict[str, float]]'

    def memory(self):
        return asizeof(self.embedded_filenames) + asizeof(self.last) + asizeof(self.tree) + asizeof(self.columns)

    def __init__(self, components=2):
        self.last = None
        self.tree = DecisionTreeClassifier()
        self.components = components
        self.columns = [f"x{i}" for i in range(self.components)]
        self.embedded_filenames = {}

    def train(self, in_df, env: Env, w: str):
        self.df = in_df.copy()

        raw_filenames = list(set(self.df.filename))
        should_prefetch = get_filenames_to_fully_prefetch(self.df, env)
        _, self.embedded_filenames = filename_embedding(raw_filenames)
        embedding_dict = self.embedded_filenames.to_dict()

        # assign add x0 x1 columns to main df
        # and set per filename
        for column in self.columns:
            def filename_to_xn(filename: str): return embedding_dict[column][filename]

            self.df[column] = self.df.filename.map(filename_to_xn)

        # trained on all filenames (there might be just 1 big file)
        X = self.embedded_filenames[self.columns].to_numpy()
        Y = self.embedded_filenames.index.map(lambda x: should_prefetch.get(x, 0.0)).to_numpy()

        self.tree.fit(X, Y)

    def _predict(self) -> 'Read | None':
        if not self.last:
            return None
        filename = self.last.filename
        values = [self.embedded_filenames[column][filename] for column in self.columns]

        if self.last.hit and self.last.offset > 0:
            return None

        should_prefetch = self.tree.predict([values])
        if should_prefetch:
            return self.last.replace(full_read=True, offset=0, length=0)
        else:
            return None

    def push(self, read: Read):
        self.last = read
