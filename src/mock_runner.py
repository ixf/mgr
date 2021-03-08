from src.methods.base import Base
from pandas import DataFrame
from .fs.mock_fuse import MockFuse
from .predicting import make_predictor
from .fs.operation import *
from .env import Env
from .progress import Progress

# simulates the recording instead of running with MockFuse
class MockRunner:
  df: DataFrame
  predictor: Base
  env: Env

  def __init__(self, df: DataFrame, predictor: "Base | None | str" = None, env: "Env | str" = 'demo'):
      if type(predictor) is str or predictor is None:
        self.predictor = make_predictor(predictor)
      elif isinstance(predictor, Base):
        self.predictor = predictor
      else:
        raise RuntimeError(f"predictor is {str(predictor)}")

      if type(env) is str:
        self.env = Env(env)
      elif isinstance(env, Env):
        self.env = env
      else:
        raise RuntimeError()

      self.df = df

  # returns basically a copy of self.df
  # but with emulated `hit`
  # ignores prefetched reads in self.df
  def run(self, progress_prefix=''):
    df = self.df
    if hasattr(df, "source"):
      df = df[df.source != 'prefetch'].copy()
    else:
      df = df.copy()
    # df = df.reset_index(drop=True)
    df["source"] = None
    df["hit"] = None
    df["timestamp"] = 0.0

    if self.predictor == None:
      print('No predictor set!')

    df_columns = df.columns[1:]
    fuse = MockFuse(df_columns, self.env)

    len_df = len(df)
    p = Progress(len_df)

    ops = [
      read_from_series(series)
      for _, series
      in df[['offset', 'filename', 'length', 'pid']].iterrows()
    ]

    for index, op in enumerate(ops):
      if p.test(index):
        p.print(f"{progress_prefix} {index}/{len_df}")

      fuse.read(op)
      if to_fetch := self._predict(op):
        fuse.read(to_fetch, prefetched=True)

    p.print(f"{progress_prefix} {len_df}/{len_df}")
    p.end()

    output_df = fuse.make_df()
    return output_df

  def _predict(self, last_read):
    if self.predictor == None:
      return

    self.predictor.push(last_read)
    to_fetch = self.predictor.predict()
    return to_fetch


