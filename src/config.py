# Simple file for loading the config.json so it can be imported easily.


import json

from os import environ
from pathlib import Path

CONFIG_PATH = "config.json"
CONFIG_FILE = Path(environ["APP_DATA_DIR"]).joinpath(CONFIG_PATH).resolve()
CONFIG_FILE.touch(exist_ok=True)

try:
    with open(CONFIG_FILE, 'r') as config_file:
        config = json.loads(config_file.read())
except json.JSONDecodeError:
    print("[Error] Failed to load configuration file! Configuration file is empty or contains invalid JSON.")
    exit(-1)
