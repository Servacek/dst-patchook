import requests
import json

from time import sleep
from bs4 import BeautifulSoup
from patch import Patch

from config import config


# URLs
KLEI_DST_UPDATES = 'http://forums.kleientertainment.com/game-updates/dst/page/{}'
DISCORD_API_BASE = "https://discord.com/api/v10"
# This doesn't contain beta versions!
#DST_BUILDS = 's3.amazonaws.com/dstbuilds/builds.json'

VERSION_CLASS_NAME = "ipsType_sectionHead ipsType_break"
MAX_ATTEMPTS = 3
RETRY_AFTER = 60 # 1 minute

PARSER = "html.parser"


def get_updates_page(page_number: int=1) -> requests.Response:
    """
    Return the game updates page for DST.

    :param page_number: The page number to retrieve. Starting from 1.

    :return: requests.Response object.
    """

    return _make_request(KLEI_DST_UPDATES.format(page_number))


webhook_info_cache = {}
def get_webhook_info(webhook_url: str, cache: bool=True) -> dict:
    """
    Retrieve and cache webhook information from a given URL.

    This function fetches the webhook information from the specified URL.
    If caching is enabled and the URL has been previously requested, it returns
    the cached data instead. The webhook data is expected to be in JSON format.

    :param webhook_url: The URL of the webhook to retrieve information from.
    :param cache: A boolean indicating whether to use cached data if available.
    :return: A dictionary containing the webhook information, or None if the
             JSON decoding fails.
    """

    global webhook_info_cache

    if webhook_url in webhook_info_cache and cache is True:
        return webhook_info_cache[webhook_url]

    response = _make_request(webhook_url)
    if response:
        try:
            webhook_info = json.loads(response.text)
        except json.JSONDecodeError:
            print("Failed to decode the webhook info JSON!")
            return {}
        else:
            webhook_info_cache[webhook_url] = webhook_info
            return webhook_info


channel_info_cache = {}
def get_channel_info(channel_id: int) -> dict:
    """
    Retrieve and cache channel information from a given channel ID.

    This function fetches the channel information from the specified channel ID.
    If caching is enabled and the channel ID has been previously requested, it returns
    the cached data instead. The channel data is expected to be in JSON format.

    :param channel_id: The channel ID to retrieve information from.
    :return: A dictionary containing the channel information, or None if the
             JSON decoding fails.
    """
    global channel_info_cache

    bot_token = config.get("bot_token")
    if not bot_token:
        return {}

    channel_url = f"{DISCORD_API_BASE}/channels/{channel_id}"
    response = requests.get(channel_url, headers={
        "Authorization": f"Bot {bot_token}"  # Replace with your bot token
    })

    if response:
        try:
            channel_info = json.loads(response.text)
        except json.JSONDecodeError:
            print("Failed to decode the webhook info JSON!")
            return {}
        else:
            channel_info_cache[channel_url] = channel_info
            return channel_info


def get_patch_soup(patch_url: str) -> BeautifulSoup:
    """
    Return the BeautifulSoup object for the given URL.
    :param patch_url: A string with the URL.
    :return: BeautifulSoup object.
    """

    return BeautifulSoup(_make_request(patch_url).text, features=PARSER)


cached_newest_version = None
def get_newest_version() -> int:
    """
    Return the highest version number from the game updates page.
    :return: An integer with the newest version.
    """

    global cached_newest_version

    if cached_newest_version is not None:
        print("Using cached newest version instead...")
        return cached_newest_version

    newest_version = None
    page_response = get_updates_page() # Newest version should be always on the first page.
    soup = BeautifulSoup(page_response.text, features=PARSER)
    for data in soup.find_all('li', {'class': 'cCmsRecord_row'}):
        version = int(
            data.find('h3', {'class': VERSION_CLASS_NAME}).contents[0].strip())
        if newest_version is None or newest_version < version:
            newest_version = version

    if newest_version:
        cached_newest_version = newest_version
        return cached_newest_version
    else:
        print("Failed to catch the newest version! Will try the next time...")
        return None


# This allows for fetching a range of versions.
def get_new_patches(min_version: int, max_version: int=None) -> list[Patch]:
    """
    Return a list of new patches with versions higher than the target version.
    :param target_version: An integer with the target version.
    :return: A list of Patch objects.
    """

    new_patches = []

    page_number = 1
    while True:
        updates_page = get_updates_page(page_number)
        soup = BeautifulSoup(updates_page.text, features="html.parser")
        last_version_fetched = None
        for data in soup.find_all('li', {'class': 'cCmsRecord_row'}):
            hotfix = "hotfix" in data.find('span').get('title').lower()

            version = int(data.find('h3', {'class': VERSION_CLASS_NAME}).contents[0].strip())
            last_version_fetched = version
            if version > min_version and (max_version is None or version < max_version):
                url = data.find('a').get("href")
                tag = data.find('span', {'class': 'ipsBadge ipsBadge_negative'})
                beta = tag and "test" in tag.text.lower() or False

                soup = get_patch_soup(url)

                new_patches.append(Patch(
                    hotfix=hotfix,
                    beta=beta,
                    version=version,
                    url=url,
                    soup=soup,
                ))

                if len(new_patches) >= config.get("max_announcements_per_webhook", 50):
                    print("[Warn] They may be even more new versions but we have already reached the limit!")
                    break

                # if config.get("debug_mode"):
                #     print("STOPPING HERE BECAUSE OF DEBUG MODE")
                #     break # Do not wait for all of the updates.

            # elif hotfix:
            #     break # Hotfixes are not pinned, but let's be sure.
            #           # It's not that much of a computational effort once we have it fetched and processed.

        # Last version on this patch is older than the target version.
        # We assume that the page is not full of pinned patches (usually only one is pinned).
        if last_version_fetched < min_version:
            break

        page_number += 1

    return new_patches


def get_specific_patch(target_version):
    return get_new_patches(target_version - 1, target_version + 1)

#### Private Helper Functions ####

# The response is optional, not using the optional annotation in order to support older versions.
def _make_request(url: str) -> requests.Response:
    """
    Make a request to the given URL and handle possible errors.
    :param url: A string with the URL.
    :return: requests.Response object.
    """

    reconnect_attempts = 0
    while reconnect_attempts <= MAX_ATTEMPTS:
        try:
            response = requests.get(url)
            print(f"[{response.status_code}]: {response.reason} <- GET {url}")
            response.raise_for_status()
            return response
        except (requests.ConnectionError, requests.exceptions.HTTPError):
            print(f"[Error] Wasn't able to fetch the page '{url}'! Retrying after {RETRY_AFTER} seconds...")
            sleep(RETRY_AFTER)
            print(f"[{reconnect_attempts}/{MAX_ATTEMPTS}] Retrying...")
            reconnect_attempts += 1

    print("Fetching failed!")
    return None
