import yaml
from logging.config import dictConfig
with open("logging.yaml") as f:
    dictConfig(yaml.load(f, Loader=yaml.SafeLoader))
