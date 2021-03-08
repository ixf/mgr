from src.env import Env
from src.predicting import make_predictor
import os
import pandas as pd
from pandas import DataFrame
from ..methods.base import Base, LearningBase
from pandas import read_csv
from typing import Callable, Any

class Grid:
  workers: 'list[str]'
  methods: 'list[str]'
  measure: 'Callable[[str, DataFrame, Base, Env], dict | None]'

  def __init__(self):
    self.workers = []
    self.methods = []

    self.dfs = {}
  
  def load_datas(self):
    for worker in self.workers:
      self.dfs[worker] = read_csv(os.path.join('traces', worker))

  def run(self, ):
    self.load_datas()

    results = []
    for method in self.methods:
      for worker in self.workers:
        name = f"{method}\t{worker}\t"

        env = Env(worker)
        env.ping = 100

        df = self.dfs[worker]

        predictor = make_predictor(method)
        self.train(predictor, df, env, worker)
        result = self.measure(name, df, predictor, env)

        if result:
          data = {'worker': worker, "method": method, **result}
          results.append(data)
    return pd.DataFrame(results)


  def train(self, method: Base, df: DataFrame, env: Env, worker_name: str):
    method.env = env
    if not isinstance(method, LearningBase): return

    method.train(df, env, worker_name)
