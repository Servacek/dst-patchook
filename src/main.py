#!/usr/bin/env python3

from os import environ
from pathlib import Path
from time import sleep

environ["APP_DIR"] = str(Path(__file__).parent.parent.absolute())
environ["APP_DATA_DIR"] = str(Path(environ["APP_DIR"]).joinpath("data"))

import version_manager

from patchook import Patchook
from patch import Patch
from web_scraper import WebScraper

from config import config


__version__ = "2.0"
__author__  = "Fi7iP"

MAX_VERSIONS_TO_ANNOUNCE = 50 if config.get("debug_mode", False) else 15

LIMIT_VERSION = 0

# Cooldown for sending the patches
POST_COOLDOWN = 5 if config.get("debug_mode", False) else 30

#############################################

web_scraper = WebScraper()

def get_patchooks() -> list[Patchook]:
    webhook_configs = config.get('webhooks', [])
    patchooks: list[Patchook] = []
    for webhook_config in webhook_configs:
        patchooks.append(Patchook(webhook_config))

    return patchooks

def main():
    patchooks = get_patchooks()
    if len(patchooks) <= 0:
        return print("No activate webhooks found.")

    print("Looking for new versions...")
    current_version = version_manager.get_saved_version()
    if current_version < 0:
        return print("No saved version found! Please update the version.txt file.")

    new_patches = web_scraper.get_new_patches(current_version)

    print("Current Version:", current_version)#, "Newest release version:", newest_version)
    if len(new_patches) <= 0:
        return print("No newer versions were found.")

    print(f"Found {len(new_patches)} new version(s)!")

    if len(new_patches) > MAX_VERSIONS_TO_ANNOUNCE:
        print("Can't announce that many versions, because of discord api limitations!")
        print(f"Will announce just the newest {MAX_VERSIONS_TO_ANNOUNCE} versions from the list.")

    # Sort depending on patch version
    patches_sorted: list[Patch] = sorted(new_patches[:MAX_VERSIONS_TO_ANNOUNCE], key=lambda patch: patch.version)
    target_version: int = patches_sorted[-1].version
    for patchook in patchooks:
        if not patchook.enabled:
            continue

        for index, patch in enumerate(patches_sorted):
            if patch.is_hotfix() and patchook.ignore_hotfix and patchook.ignore_beta:
                continue

            # Support for release only webhooks
            if patch.is_beta() and patchook.ignore_beta:
                continue

            # Support for beta only webhooks
            if patch.is_release() and patchook.ignore_release and patchook.ignore_major:
                continue

            if patch.is_major() and patchook.ignore_major:
                continue

            response = patchook.post(patch)
            if response is None or not response.ok:
                return print("[Error] Failed to post the update on discord!")

            # Do not cooldown when this is the last patch
            if index < (len(patches_sorted) - 1):
                print(f"Cooling down!")
                sleep(POST_COOLDOWN)

            if config.get('debug_mode', False) and LIMIT_VERSION > 0 and patch.version == LIMIT_VERSION:
                break

    if not config.get('debug_mode', False):
        print("Updating the saved version...")
        version_manager.update_saved_version(target_version) # updates the version to the newest
    else:
        print("[Warning]: Debug mode enabled!")

    print("Done!")



if __name__ == "__main__":
    main()
