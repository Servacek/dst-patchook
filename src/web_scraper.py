import requests
import json
import re

from dateutil import parser

from time import sleep
from bs4 import BeautifulSoup
from post import Post, PostTag

from config import config


# URLs
KLEI_DST_UPDATES = 'http://forums.kleientertainment.com/game-updates/dst/page/{}'
DISCORD_API_BASE = "https://discord.com/api/v10"
# This doesn't contain beta versions!
#DST_BUILDS = 's3.amazonaws.com/dstbuilds/builds.json'

VERSION_CLASS_NAME = "ipsType_sectionHead ipsType_break"
MAX_ATTEMPTS = 3
RETRY_AFTER = 60 # 1 minute

MAX_FORUM_SEARCH_DEPTH = 1

PARSER = "html.parser" # TODO: Update to lxml?


def get_source_url_page(url: str, page_number: int=1) -> BeautifulSoup:
    """
    Return the game updates page for DST.

    :param page_number: The page number to retrieve. Starting from 1.

    :return: requests.Response object.
    """

    response = _make_request(url + "/page/" + str(page_number))
    if response is None:
        return BeautifulSoup("", features=PARSER)
    return BeautifulSoup(response.text, features=PARSER)


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

    if channel_url in channel_info_cache:
        return channel_info_cache[channel_url]

    response = requests.get(channel_url, headers={
        "Authorization": f"Bot {bot_token}"
    })

    if response:
        try:
            channel_info = json.loads(response.text)
        except json.JSONDecodeError:
            print("Failed to decode the channel info JSON!")
            return {}
        else:
            channel_info_cache[channel_url] = channel_info
            return channel_info


def get_post_soup(patch_url: str) -> BeautifulSoup:
    """
    Return the BeautifulSoup object for the given URL.
    :param patch_url: A string with the URL.
    :return: BeautifulSoup object.
    """

    response = _make_request(patch_url)
    if response is None:
        return None
    return BeautifulSoup(response.text, features=PARSER)


cached_newest_version = {}
def get_newest_version(url: str) -> int:
    """
    Return the highest version number from the game updates page.
    :return: An integer with the newest version.
    """

    global cached_newest_version

    if url in cached_newest_version:
        print("Using cached newest version instead...")
        return cached_newest_version[url]

    newest_version = None
    soup = get_source_url_page(url)  # Newest version should be always on the first page.
    for data in soup.find_all('li', {'class': 'cCmsRecord_row'}):
        version = int(
            data.find('h3', {'class': VERSION_CLASS_NAME}).contents[0].strip())
        if newest_version is None or newest_version < version:
            newest_version = version

    if newest_version:
        cached_newest_version[url] = newest_version
        return cached_newest_version[url]
    else:
        print("Failed to catch the newest version! Will try the next time...")
        return None


# def get_new_posts_from_rss(url: str, min_version: int, max_version: int=None) -> list[Post]:
#     response = _make_request(url)
#     if response.status_code != 200:
#         print(f"Failed to fetch the RSS feed from {url}. Status code: {response.status_code}")
#         return []

#     version_regex = re.compile(r'<title>(\d+)</title>\s*<link>\s*https://forums.kleientertainment.com/game-updates/dst/(\d+-r\d+)/\s*</link>')
#     matches = version_regex.search(response.text)
#     version = matches.group(1) if matches else None
#     url_id = matches.group(2) if matches else None




# This allows for fetching a range of versions.
def get_new_posts(url: str, min_version: int, max_version: int=None) -> list[Post]:
    """
    Return a list of new patches with versions higher than the target version.
    :param target_version: An integer with the target version.
    :return: A list of Post objects.
    """

    new_posts = []

    last_version_fetched = None
    page_number = 1
    while True:
        soup = get_source_url_page(url, page_number=page_number)
        records = soup.find_all('li', {'class': 'cCmsRecord_row'})
        for data in records:
            a = data.find("a")
            release_id = int(a.get("data-releaseid"))
            #release_id = int(data.find('h3', {'class': VERSION_CLASS_NAME}).contents[0].strip())
            last_version_fetched = release_id
            if release_id > min_version and (max_version is None or release_id < max_version):
                post_url = a.get("href")
                # post_soup = get_post_soup(post_url)

                # full_title = post_soup.find("h1", {"class": "ipsType_pageTitle ipsType_largeTitle ipsType_break"})
                # full_title_text = full_title and full_title.text and full_title.text.strip() or None
                # print(full_title_text)
                # exit()

                # Add the apropriate tags
                version = int(data.find('h3', {'class': VERSION_CLASS_NAME}).contents[0].strip())
                tag = data.find('span', {'class': 'ipsBadge ipsBadge_negative'})
                post = Post(
                    PostTag.UPDATE,
                    PostTag.HOTFIX if (s := data.find('span')) and s.get('title') and "hotfix" in s.get('title').lower() else None,
                    PostTag.BETA if tag and tag.text and "test" in tag.text.lower() or False else None,

                    url=post_url,
                    soup=get_post_soup(post_url),
                    source_url=url,
                    version=version
                )
                post.release_id = release_id
                new_posts.append(post)

                if len(new_posts) >= config.get("max_announcements_per_webhook", 50):
                    print("[Warn] They may be even more new versions but we have already reached the limit!")
                    return new_posts

        if not records:
            for post in soup.find_all("div" , {"class": "ipsDataItem_main"}):
                post_author = post.find("div", {"class": "ipsDataItem_meta"}).find("a")

                dev = False
                for span in post_author.find_all("span"):
                    span_style = span.get("style")
                    # "color:goldenrod" (for mods)
                    # "color:red" (for devs and admins)
                    if span_style and "color:red" in span_style.lower().replace(" ", ""):
                        dev = True
                        break
                if not dev:
                    continue

                timestamp = int(parser.parse(post.find("time").get("datetime")).timestamp())
                last_version_fetched = timestamp
                if timestamp > min_version and (max_version is None or timestamp < max_version):
                    post_url = post.find("span", {"class": "ipsType_break ipsContained"}).find("a").get("href")
                    soup = get_post_soup(post_url)
                    article = soup.find("article")
                    if article and [link.get("href") for link in article.find_all("a") if str(link.text).lower() == "view full update"]:
                        continue # Skip updates since they are already announced separately.

                    post = Post(url=post_url, soup=soup, source_url=url)
                    post.add_tag(PostTag.FORUM_POST)
                    new_posts.append(post)

                    if len(new_posts) >= config.get("max_announcements_per_webhook", 50):
                        print("[Warn] They may be even more new versions but we have already reached the limit!")
                        return new_posts

            if page_number == MAX_FORUM_SEARCH_DEPTH: # If we reach the maximal depth
                break

        # Last version on this post is older than the target version.
        # We assume that the page is not full of pinned patches (usually only one is pinned).
        if not last_version_fetched or last_version_fetched < min_version:
            break

        page_number += 1

    # NOTE: This is in case we would also use the RSS feed as a backup.
    # Remove duplicate posts since we use multiple systems for fetching.
    # seen_versions = set()
    # for post in new_posts[:]:
    #     if post.version in seen_versions:
    #         new_posts.remove(post)
    #     else:
    #         seen_versions.add(post.version)

    return new_posts


def get_specific_patch(target_version):
    return get_new_posts(target_version - 1, target_version + 1)

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
