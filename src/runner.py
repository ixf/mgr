import yaml
import os
import logging
from typing import *
from .env import Env
from .predicting import Base, make_predictor
from .low_level_runner import LowLevelRunner
from .stats import make_df

log = logging.getLogger("run")

pwd = os.getcwd()
target_path = f"{pwd}/target"

# high level runner
# enter preset name + customize
class Runner:
  def __init__(self, name: str = None, env = None, predictor=None, workers='workers.yaml'):
    with open(workers) as f:
      self.yml = yaml.load(f, Loader=yaml.SafeLoader)
    self._env: Optional[Env] = None
    self._cmd: Optional[str] = None
    self._pr: Optional[Base] = None
    if name:
      self.select(name)
    if env:
      self.env(env)
    if predictor:
      self.prd(predictor)

  def cmd(self, cmd: str):
    self._cmd = cmd
    return self

  def select(self, name: str):
    d = self.yml[name]
    self.data: Dict = d
    self._cmd = d['cmd']
    if 'env' in d:
      self._env = Env(d['env'])
    return self

  def env(self, e: Union[str, Env]):
    if type(e) is str:
      self._env = Env(e)
    elif type(e) is Env:
      self._env = e
    return self

  def prd(self, pr):
    if type(pr) == str:
      self._pr = make_predictor(pr)
    elif pr.__class__.__name__ == 'type':
      self._pr = pr()
    elif pr:
      self._pr = pr
    return self

  def _template(self, s):
    worker_dir = f"{pwd}/workers"
    if d := self.data.get('dir'):
      worker_dir = f"{worker_dir}/{d}"

    return s.format(
      target=target_path,
      worker=worker_dir
    )


  async def run(self, timeout=60*60, debug=False, show_output=True):
    cmd = self._template(self._cmd)

    env = self._env or Env()

    if self._pr == None:
      log.info('No predictor set')

    r = LowLevelRunner(
      cmd,
      env,
      self._pr,
      timeout=timeout,
      debug=debug,
      show_output=show_output
    )
    fuse = await r.run()
    return make_df(fuse)
