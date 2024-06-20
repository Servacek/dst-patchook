import requests

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
VIDEO_EMBED_ID_TEMPLATE = "((?<=(v|V)/)|(?<=be/)|(?<=(\?|\&)v=)|(?<=embed/))([\w-]+)"

PARSER = "html.parser"


class WebScraper:
    """
    A class for web scraping and requesting game updates page for DST.
    """

    def get_updates_page(self) -> requests.Response:
        """
        Return the game updates page for DST.
        :return: requests.Response object.
        """

        return self._make_request(KLEI_DST_UPDATES)

    def get_patch_soup(self, patch_url: str) -> BeautifulSoup:
        """
        Return the BeautifulSoup object for the given URL.
        :param patch_url: A string with the URL.
        :return: BeautifulSoup object.
        """

        return BeautifulSoup(self._make_request(patch_url).text, features=PARSER)

    def get_new_patches(self, target_version: int) -> list[Patch]:
        """
        Return a list of new patches with versions higher than the target version.
        :param target_version: An integer with the target version.
        :return: A list of Patch objects.
        """

        new_patches = []

        updates_page = self.get_updates_page()
        soup = BeautifulSoup(updates_page.text, features="html.parser")
        for data in soup.find_all('li', {'class': 'cCmsRecord_row'}):
            hotfix = "hotfix" in data.find('span').get('title').lower()

            version = int(data.find('h3', {'class': VERSION_CLASS_NAME}).contents[0].strip())
            if version > target_version:
                url = data.find('a').get("href")
                tag = data.find('span', {'class': 'ipsBadge ipsBadge_negative'})
                beta = tag and "test" in tag.text.lower() or False

                soup = self.get_patch_soup(url)

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

    def _make_request(self, url: str) -> requests.Response:
        """
        Make a request to the given URL and handle possible errors.
        :param url: A string with the URL.
        :return: requests.Response object.
        """

        reconnect_attempts = 0
        while reconnect_attempts <= MAX_ATTEMPTS:
            try:
                request = requests.get(url)
                request.raise_for_status()
                return request
            except (requests.ConnectionError, requests.exceptions.HTTPError):
                print(f"[Error] Wasn't able to fetch the page '{url}'!")
                sleep(300)
                print(f"[{reconnect_attempts}/{MAX_ATTEMPTS}] Retrying...")
                reconnect_attempts += 1
