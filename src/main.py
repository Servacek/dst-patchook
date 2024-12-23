#!/usr/bin/env python3

from os import environ
from pathlib import Path
from time import sleep

environ["APP_DIR"] = str(Path(__file__).parent.parent.absolute())
environ["APP_DATA_DIR"] = str(Path(environ["APP_DIR"]).joinpath("data"))

from patchook import Patchook
from patch import Patch
import web_scraper

from config import config, save_config


__version__ = "2.7"
__author__  = "Fi7iP"


# The discord REST API rate limit is 16 requests/second.
# So at most one request every 3 seconds.
# Cooldown for sending the patches
POST_COOLDOWN = config.get("post_cooldown", 5)
MAX_VERSIONS_TO_ANNOUNCE = config.get("max_announcements_per_webhook", 50)
LIMIT_VERSION = 0 # Version where we should break at.

#############################################

def announce_new_versions(patchooks):
    # Skip disabled webhooks here since they are not going to post the updates anyway.
    last_announced_versions = [patchook.last_announced_version for patchook in patchooks if patchook.last_announced_version is not None and patchook.enabled is True]
    oldest_announced_version = min(last_announced_versions)
    print("[Info] Looks like the oldest announced version we have is", oldest_announced_version)

    print("[Info] Looking for versions newer than that...")
    new_patches = web_scraper.get_new_patches(oldest_announced_version)
    if len(new_patches) <= 0:
        return print("No newer versions were found.")
    print(f"[Info] Found {len(new_patches)} new version(s)!")

    if len(new_patches) > MAX_VERSIONS_TO_ANNOUNCE:
        print("[Warn] Can't announce that many versions, because of discord api limitations!")
        print(f"[Warn] Will announce just the newest {MAX_VERSIONS_TO_ANNOUNCE} versions from the list.")

    # Sort depending on patch version
    patches_sorted: list[Patch] = sorted(new_patches[:MAX_VERSIONS_TO_ANNOUNCE], key=lambda patch: patch.version)
    for patchook in patchooks:
        if not patchook.enabled:
            print(f"[Info] Webhook {patchook.name or patchook.url} from guild {patchook.guild_id or 'UNKNOWN'} is disabled. Skipping...")
            continue

        if patchook.last_announced_version is None:
            continue # We asked the user to update the config file manually and supply the newest version.

        for index, patch in enumerate(patches_sorted):
            if patch.version <= patchook.last_announced_version and not config.get('debug_mode', False):
                continue # Only publish version that were not published before by this webhook.

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

            # Continue even when some updates fail to be announced.
            try:
                response = patchook.post(patch)
                if response is None or not response.ok:
                    raise Exception("[Error] Posting request returned an error status code!")
            except Exception as err:
                print("[Error] Failed to post the update on discord!", err)
            else: # In case they were no errors
                patchook.last_announced_version = patch.version
                patchook.config["last_announced_version"] = patch.version

            # Rate limiting is handled per IP not per endpoint or webhook.
            # Do not cooldown when this is the last patch
            if index < (len(patches_sorted) - 1):
                print(f"Cooling down!")
                sleep(POST_COOLDOWN)

            if config.get('debug_mode', False) and LIMIT_VERSION > 0 and patch.version == LIMIT_VERSION:
                break


def main():
    webhook_configs = config.get('webhooks', [])
    patchooks: list[Patchook] = []
    for webhook_config in webhook_configs:
        patchooks.append(Patchook(webhook_config))

    if len(patchooks) <= 0: # There is nothing for us to do.
        return print("[Warn] No webhooks found. Add some in your config.json file!\nCheck the example_config.json for reference.")

    announce_new_versions(patchooks)

    if config.get('debug_mode', False):
        # In debug mode we do not override the configurations so we can test one update
        # multiple times without manually modifying the files back each time.
        print("[Warning]: Debug mode enabled!")
    else:
        updated_webhook_configs = [patchook.config for patchook in patchooks]
        if updated_webhook_configs != webhook_configs:
            print("[Info] Webhook configurations have changed during announcing process! Saving the updates...")
            config["webhooks"] = updated_webhook_configs
            save_config()

    print("[Info] Done!")



if __name__ == "__main__":
    main()
