from typing import Dict
from src.fs.operation import Read
from src.env import Env, size_to_human
from pandas import DataFrame
import numpy as np 
import random
import abc
from time import time

class Base:
    __metaclass__ = abc.ABCMeta
    env: Env = None
    time = 0

    @abc.abstractmethod
    def push(self, read: Read):
        pass

    @abc.abstractmethod
    def _predict(self) -> Read:
        pass

    @abc.abstractmethod
    def memory(self) -> float:
        pass

    def resources_used(self) -> Dict[str, 'str | float']:
        m = self.memory()
        return {
            'memory': m and size_to_human(m),
            'time': self.time
        }

    def predict(self) -> Read:
        a = time()
        predicted = self._predict()
        b = time()
        self.time += b-a
        return predicted

class LearningBase(Base):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def train(self, df: DataFrame, env: Env, worker_name: str = '', split: float = 0.2):
        pass

    def split(self, length: int, split: float):
        idx = np.arange(length)
        random.shuffle(idx)
        pivot = int(len(idx) * (1.0 - split))
        i_train = idx[:pivot]
        i_test = idx[pivot:]
        return (i_train, i_test)

class Noop(Base):
    def push(self, _):
        pass

    def predict(self):
        pass

