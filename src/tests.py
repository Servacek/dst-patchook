from pathlib import Path
from os import environ

environ["APP_DIR"] = str(Path(__file__).parent.parent.absolute())
environ["APP_DATA_DIR"] = str(Path(environ["APP_DIR"]).joinpath("data"))

from web_scraper import WebScraper

from patch import Patch
from patchook import Patchook

from config import config


if __name__ == '__main__':
    patchook = Patchook(config['webhooks'][0])
    web_scraper = WebScraper()

    ######################################################################

    print("Lenght and identation test:")
    url = "https://forums.kleientertainment.com/game-updates/dst/498339-r1756/"
    patchook.post(Patch(
        hotfix=True,
        beta=True,
        version=498339,
        url=url,
        soup=web_scraper.get_patch_soup(url),
    ))

    # ######################################################################

    print("Spoiler test and category alignment test:")
    url = "https://forums.kleientertainment.com/game-updates/dst/490507-r1720/"
    patchook.post(Patch(
        hotfix=True,
        beta=True,
        version=497159,
        url=url,
        soup=web_scraper.get_patch_soup(url),
    ))

    # ######################################################################

    print("Release Thumbnail Test:")
    url = "https://forums.kleientertainment.com/game-updates/dst/538959-r1935/"
    patchook.post(Patch(
        hotfix=False,
        beta=False,
        version=538959,
        url=url,
        soup=web_scraper.get_patch_soup(url),
    ))

    # ######################################################################

    print("Hotfix Thumbnail Test")
    url = "https://forums.kleientertainment.com/game-updates/dst/542788-r1950/"
    patchook.post(Patch(
        hotfix=True,
        beta=False,
        version=542788,
        url=url,
        soup=web_scraper.get_patch_soup(url),
    ))

    # ######################################################################

    print("Release test:")
    url = "https://forums.kleientertainment.com/game-updates/dst/490507-r1720/"
    patchook.post(Patch(
        hotfix=False,
        beta=False,
        version=497159,
        url=url,
        soup=web_scraper.get_patch_soup(url),
    ))

    # ######################################################################

    print("Lenght test:")
    url = "https://forums.kleientertainment.com/game-updates/dst/565757-r2033/"
    patchook.post(Patch(
        hotfix=True,
        beta=True,
        version=565757,
        url=url,
        soup=web_scraper.get_patch_soup(url),
    ))

    # ######################################################################

    print("Hyperlink test:")
    url = "https://forums.kleientertainment.com/game-updates/dst/472550-r1614/"
    patchook.post(Patch(
        hotfix=True,
        beta=True,
        version=472550,
        url=url,
        soup=web_scraper.get_patch_soup(url),
    ))

    # ######################################################################

    print("Hyperlink and beta detection test")
    url = "https://forums.kleientertainment.com/game-updates/dst/460309-r1525/"
    patchook.post(Patch(
        hotfix=True,
        beta=True,
        version = 460309,
        url=url,
        soup=web_scraper.get_patch_soup(url),
    ))

    # # ######################################################################

    print("Underline formatting and description test")
    url = "https://forums.kleientertainment.com/game-updates/dst/443039-r1351/"
    patchook.post(Patch(
        hotfix=True,
        beta=True,
        version = 443039,
        url=url,
        soup=web_scraper.get_patch_soup(url),
    ))

    # ######################################################################

    print("Emoji and multiple sections test:")
    url = "https://forums.kleientertainment.com/game-updates/dst/174200-r39/"
    patchook.post(Patch(
        hotfix=True,
        beta=True,
        version = 174200,
        url=url,
        soup=web_scraper.get_patch_soup(url),
    ))

    # ######################################################################

    print("Rewardlink fetch test")
    url = "https://forums.kleientertainment.com/game-updates/dst/600267-r2174/"
    patchook.post(Patch(
        hotfix=False,
        beta=False,
        version=600267,
        url=url,
        soup=web_scraper.get_patch_soup(url),
    ))

    # ######################################################################

    url = "https://forums.kleientertainment.com/game-updates/dst/499972-r1765/"
    patchook.post(Patch(
        hotfix=True,
        beta=False,
        version=499972,
        url=url,
        soup=web_scraper.get_patch_soup(url)
    ))

    # ######################################################################

    print("Description test")
    url = "https://forums.kleientertainment.com/game-updates/dst/499819-r1764/"
    patchook.post(Patch(
        hotfix=True,
        beta=False,
        version=499819,
        url=url,
        soup=web_scraper.get_patch_soup(url)
    ))

    ######################################################################

    print("Code Block Test")
    url = "https://forums.kleientertainment.com/game-updates/dst/528116-r1891/"
    patchook.post(Patch(
        hotfix=True,
        beta=False,
        version=528116,
        url=url,
        soup=web_scraper.get_patch_soup(url)
    ))

    # ######################################################################

    print("Multiple rewardlink fetch test")
    url = "https://forums.kleientertainment.com/game-updates/dst/605310-r2186/"
    patchook.post(Patch(
        hotfix=False,
        beta=False,
        version=605310,
        url=url,
        soup=web_scraper.get_patch_soup(url),
    ))
