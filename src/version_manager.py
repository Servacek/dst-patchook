from os import environ
from pathlib import Path


VERSION_PATH = "version.txt"
VERSION_FILE = Path(environ["APP_DATA_DIR"]).joinpath(VERSION_PATH).resolve()
VERSION_FILE.touch(exist_ok=True)


def get_saved_version() -> int:
    """Return the saved version"""

    with open(VERSION_FILE, 'r') as file:
        return int(file.read().strip() or -1)

def update_saved_version(version: int) -> None:
    """Open the version file in w+ mode and save the added version"""

    with open(VERSION_FILE, 'w+') as version_file:
        version_file.write(str(version))
