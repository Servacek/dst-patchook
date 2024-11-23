import requests
import json

from time import sleep
from bs4 import BeautifulSoup
from patch import Patch

from config import config


# URLs
KLEI_DST_UPDATES = 'http://forums.kleientertainment.com/game-updates/dst/'
# This doesn't contain beta versions!
#DST_BUILDS = 's3.amazonaws.com/dstbuilds/builds.json'

VERSION_CLASS_NAME = "ipsType_sectionHead ipsType_break"
MAX_ATTEMPTS = 3
RETRY_AFTER = 60 # 1 minute

PARSER = "html.parser"


def get_updates_page() -> requests.Response:
    """
    Return the game updates page for DST.
    :return: requests.Response object.
    """

    return _make_request(KLEI_DST_UPDATES)


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

    if webhook_url in webhook_info_cache and cache is True:
        return webhook_info_cache[webhook_url]

    response = _make_request(webhook_url)
    if response:
        try:
            webhook_info = json.loads(response.text)
        except json.JSONDecodeError:
            print("Failed to decode the webhook info JSON!")
            return None
        else:
            webhook_info_cache[webhook_url] = webhook_info
            return webhook_info



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

    if cached_newest_version is not None:
        print("Using cached newest version instead...")
        return cached_newest_version

    page_response = get_updates_page()
    soup = BeautifulSoup(page_response.text, features=PARSER)

    versions = []
    for data in soup.find_all('li', {'class': 'cCmsRecord_row'}):
        version = int(
            data.find('h3', {'class': VERSION_CLASS_NAME}).contents[0].strip())
        versions.append(version)

    if versions:
        cached_newest_version = max(versions)
        return cached_newest_version
    else:
        print("Failed to catch the newest version! Will try the next time...")
        return None


def get_new_patches(target_version: int) -> list[Patch]:
    """
    Return a list of new patches with versions higher than the target version.
    :param target_version: An integer with the target version.
    :return: A list of Patch objects.
    """

    new_patches = []

    updates_page = get_updates_page()
    soup = BeautifulSoup(updates_page.text, features="html.parser")
    for data in soup.find_all('li', {'class': 'cCmsRecord_row'}):
        hotfix = "hotfix" in data.find('span').get('title').lower()

        version = int(data.find('h3', {'class': VERSION_CLASS_NAME}).contents[0].strip())
        if version > target_version:
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

            if config["debug_mode"]:
                break # Do not wait for all of the updates.

        elif hotfix:
            break

    return new_patches

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
