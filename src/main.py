#!/usr/bin/env python3

from os import environ
from pathlib import Path
from time import sleep

environ["APP_DIR"] = str(Path(__file__).parent.parent.absolute())
environ["APP_DATA_DIR"] = str(Path(environ["APP_DIR"]).joinpath("data"))

from patchook import Patchook
from post import Post
import web_scraper

from config import config, save_config


__version__ = "3.0"
__author__  = "Fi7iP"


# The discord REST API rate limit is 16 requests/second.
# So at most one request every 3 seconds.
# Cooldown for sending the patches
POST_COOLDOWN = config.get("post_cooldown", 5)
COOLDOWN_FREQUENCY = 3 # Every X posts for "POST_COOLDOWN" seconds
RETRY_AFTER_RESERVE = 60 # To compensate any clock drift
RETRY_AFTER_DEFAULT = 60 - RETRY_AFTER_RESERVE
GATEWAY_UNVAILABLE_SLEEP = 60
MAX_VERSIONS_TO_ANNOUNCE = config.get("max_announcements_per_webhook", 50)
LIMIT_VERSION = 0 # Version where we should break at.

#############################################

def announce_new_versions(patchooks: list[Patchook]):
    if len(patchooks) <= 0: # There is nothing for us to do.
        return print("[Info] No enabled webhooks found.")

    # We have to calculate all the patches we need to post and then sort them by their publishDate.
    # Skip disabled webhooks here since they are not going to post the updates anyway.
    oldest_announced_versions = {} # Oldest versions for each source_url
    for patchook in patchooks:
        for source_url, version in patchook.last_announced_version.items():
            if version is not None and version < oldest_announced_versions.get(source_url, version + 1):
                oldest_announced_versions[source_url] = version

    # We take all versions since some may be useful for one webhook and some for the others.
    patches_to_post = []
    for source_url, version in oldest_announced_versions.items():
        print("[Info] Looks like the oldest announced version we have for source ", source_url, " is", version)
        patches_to_post.extend(web_scraper.get_new_posts(source_url, version))

    if len(patches_to_post) <= 0:
        return print("No newer posts were found.")

    print(f"[Info] Announcing {len(patches_to_post)} new post(s) to {len(patchooks)} webhooks...")

    if len(patches_to_post) > MAX_VERSIONS_TO_ANNOUNCE:
        print(f"[Warn] Will announce just the newest {MAX_VERSIONS_TO_ANNOUNCE} post(s) from the list.")

    # Sort depending on post publish timestamp because we have patches from various sources.
    patches_sorted: list[Post] = sorted(patches_to_post[:MAX_VERSIONS_TO_ANNOUNCE],
        key=lambda post: post.publish_timestamp or post.version
    )
    for patchook in patchooks:
        for index, post in enumerate(patches_sorted):
            if not patchook.can_post(post):
                continue

            # Continue even when some updates fail to be announced.
            # try:
            response = patchook.post(post)
            if response is None or not response.ok:
                if response and response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", RETRY_AFTER_DEFAULT)) + RETRY_AFTER_RESERVE
                    print(f"[Error] Discord API rate limit reached! Retrying in {retry_after} seconds...")
                    sleep(retry_after)
                    continue
                elif response and response.status_code == 502:
                    sleep(GATEWAY_UNVAILABLE_SLEEP)
                    continue
                else:
                    raise Exception("[Error] Posting request returned an no-retry error status code! " + str(post))
            # except Exception as err:
            #     print("[Error] Failed to post the update on discord!", err)

            # Rate limiting is handled per IP not per endpoint or webhook.
            # Do not cooldown when this is the last post
            if index < (len(patches_sorted) - 1) and (index + 1) % COOLDOWN_FREQUENCY == 0:
                print(f"Cooling down for {POST_COOLDOWN} seconds!")
                sleep(POST_COOLDOWN)


def main():
    webhook_configs = config.get('webhooks', [])
    if not webhook_configs: # There is nothing for us to do.
        return print("[Warn] No webhooks found. Add some in your config.json file!\nCheck the example_config.json for reference.")

    patchooks: list[Patchook] = []
    for webhook_config in webhook_configs:
        if webhook_config.get("enabled", True) is False: # All webhooks are enabled by default
            name = webhook_config.get("name", webhook_config.get("url"))
            guild = webhook_config.get("guild_id", "UNKNOWN")
            print(f"[Info] Webhook \"{name}\" from guild \"{guild}\" is disabled. Skipping...")
            continue

        patchooks.append(Patchook(webhook_config))

    announce_new_versions(patchooks)

    if config.get('debug_mode', False):
        # In debug mode we do not override the configurations so we can test one update
        # multiple times without manually modifying the files back each time.
        print("[Warning]: Debug mode enabled! Configuration updates won't be saved.")
    else:
        updated_webhook_configs = [patchook.config for patchook in patchooks]
        if updated_webhook_configs != webhook_configs:
            print("[Info] Webhook configurations have changed during announcing process! Saving the updates...")
            config["webhooks"] = updated_webhook_configs
            save_config()

    print("[Info] Done!")



if __name__ == "__main__":
    main()
