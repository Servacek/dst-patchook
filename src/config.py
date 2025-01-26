# Simple file for loading the config.json so it can be imported easily.


import json

from os import environ
from pathlib import Path

CONFIG_PATH = "config.json"
CONFIG_FILE = Path(environ["APP_DATA_DIR"]).joinpath(CONFIG_PATH).resolve()
CONFIG_FILE.touch(exist_ok=True)

try:
    with open(CONFIG_FILE, 'r') as config_file:
        config_str = config_file.read()
        config_str = "\n".join([line for line in config_str.splitlines() if not line.strip().startswith("//")])
        config = json.loads(config_str)
except json.JSONDecodeError:
    print("[Error] Failed to load configuration file! Configuration file is empty or contains invalid JSON.")
    exit(-1)

def save_config():
    with open(CONFIG_FILE, 'w') as config_file:
        config_file.write(json.dumps(config, indent=4))
        print("[Info] Configuration file saved.")
