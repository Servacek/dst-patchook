import re

from pathlib import Path
from os import environ
from bs4 import BeautifulSoup

environ["APP_DIR"] = str(Path(__file__).parent.parent.absolute())
environ["APP_DATA_DIR"] = str(Path(environ["APP_DIR"]).joinpath("data"))

import web_scraper

from post import Post, PostTag
from patchook import Patchook

from config import config

# UPDATE_SOURCE_DST = "https://forums.kleientertainment.com/game-updates/dst"
# UPDATE_SOURCE_ONI = "https://forums.kleientertainment.com/game-updates/oni-alpha/"
# UPDATE_SOURCE_ROTWOOD = "https://forums.kleientertainment.com/game-updates/rotwood-ea"
# UPDATE_SOURCE_DS = "https://forums.kleientertainment.com/game-updates/dont_starve/"

FULL_UPDATE_URL_PATTERN  = re.compile(r'https:\/\/forums.kleientertainment.com\/game-updates\/.+\/(\d+)-r\d+\/?')
FORUM_UPDATE_URL_PATTERN = re.compile(r'https:\/\/forums.kleientertainment.com\/forums\/topic\/.+\-game\-update\-(\d+)\/?')

patchook = Patchook(config.get("webhooks")[0])

def test_tags():
    post = Post(
        url="https://forums.kleientertainment.com/game-updates/dst/651101-r2457/#change-list",
        soup=None,
        source_url="https://forums.kleientertainment.com/game-updates/dst/"
    )

    print("Adding tags test")
    post.add_tag(PostTag.BETA)
    post.add_tag(PostTag.HOTFIX)
    assert(post.has_tag(PostTag.BETA) and not post.has_tag(PostTag.UPDATE))
    post.add_tag(PostTag.UPDATE)
    assert(post.has_tag(PostTag.BETA) and post.has_tag(PostTag.UPDATE))

    post.tags = [PostTag.BETA, PostTag.HOTFIX, PostTag.UPDATE, PostTag.FORUM_POST]

    assert(post.meets_tag_rule("forum"))

    assert(not post.meets_tag_rule("forum !hotfix !trailer"))

    tag_rule = "forum"
    assert(post.meets_tag_rule(tag_rule))

    post.tags = []
    tags = [PostTag.BETA, PostTag.HOTFIX, PostTag.UPDATE, PostTag.FORUM_POST]
    post.add_tags(tags[0], *tags[1:])
    for tag in tags:
        assert(post.has_tag(tag))

def post_update(url: str, *tags: PostTag) -> Post:
    match = FULL_UPDATE_URL_PATTERN.match(url) or FORUM_UPDATE_URL_PATTERN.match(url)

    tags = list(tags)
    if not PostTag.ANNOUNCEMENT in tags:
        tags.append(PostTag.UPDATE)

    post = Post(
        PostTag.UPDATE,
        *tags,
        version=match and match.group(1) or 1,
        url=url,
        soup=web_scraper.get_post_soup(url),
    )

    return patchook.post(post)


if __name__ == '__main__':
    ######################################################################

    # test_tags()
    # print("TAG TESTS PASSED!")

    # print("General Announcement Test")
    # post_update("https://forums.kleientertainment.com/announcement/89-rift-of-the-necrodancer-is-out-now/")

    # ######################################################################

    # print("Roadmap Test")
    # post_update("https://forums.kleientertainment.com/forums/topic/154074-dont-starve-together-2024-roadmap/")

    # ######################################################################

    # print("Griftlands Test")
    # post_update("https://forums.kleientertainment.com/forums/topic/131380-game-update-469524/")

    # ######################################################################

    # print("Hot Lava Test")
    # post_update("https://forums.kleientertainment.com/game-updates/hot-lava/532185-r1909/")

    # ######################################################################

    # print("ONI Test")
    # post_update("https://forums.kleientertainment.com/game-updates/rotwood-ea/653315-r2468/")

    # ######################################################################

    print("DS Test")
    post_update("https://forums.kleientertainment.com/game-updates/dont_starve/554439-r1998/")

    # ######################################################################

    # print("Rotwood Test")
    # post_update("https://forums.kleientertainment.com/game-updates/rotwood-ea/653315-r2468/")

    # ######################################################################

    # print("Forum test")
    # post_update("https://forums.kleientertainment.com/game-updates/dst/651101-r2457/")

    # ######################################################################

    print("Post with separated images test")
    post_update("https://forums.kleientertainment.com/game-updates/dst/631099-r2391/")

    # print("THICC UPDATE")
    # post_update("https://forums.kleientertainment.com/forums/topic/160348-dont-starve-together-hallowed-nights-returns/")

    print("Intermission Test")
    post_update("https://forums.kleientertainment.com/game-updates/dst/624447-r2377/")

    # print("Test with a gif")
    # post_update("https://forums.kleientertainment.com/game-updates/dst/651101-r2457/")

    # # ######################################################################

    # print("Lenght and identation test:")
    # post_update("https://forums.kleientertainment.com/game-updates/dst/498339-r1756/")

    # # # ######################################################################

    # print("Spoiler test and category alignment test:")
    # post_update("https://forums.kleientertainment.com/game-updates/dst/490507-r1720/")

    # # ######################################################################

    # print("Release Thumbnail Test:")
    # post_update("https://forums.kleientertainment.com/game-updates/dst/538959-r1935/")

    # # # ######################################################################

    # print("Hotfix Thumbnail Test")
    # post_update("https://forums.kleientertainment.com/game-updates/dst/542788-r1950/")

    # # ######################################################################

    # print("Release test:")
    # post_update("https://forums.kleientertainment.com/game-updates/dst/490507-r1720/")

    # # ######################################################################

    # print("Lenght test:")
    # post_update("https://forums.kleientertainment.com/game-updates/dst/565757-r2033/")

    # # # ######################################################################

    # print("Hyperlink test:")
    # post_update("https://forums.kleientertainment.com/game-updates/dst/472550-r1614/")

    # # ######################################################################

    # print("Hyperlink and beta detection test")
    # post_update("https://forums.kleientertainment.com/game-updates/dst/460309-r1525/")

    # # # ######################################################################

    # print("Underline formatting and description test")
    # post_update("https://forums.kleientertainment.com/game-updates/dst/443039-r1351/")

    # # ######################################################################

    # print("Emoji and multiple sections test:")
    # post_update("https://forums.kleientertainment.com/game-updates/dst/174200-r39/")

    # # ######################################################################

    # print("Rewardlink fetch test")
    # post_update("https://forums.kleientertainment.com/game-updates/dst/600267-r2174/")

    # # ######################################################################

    # print("Spoiler test (with images) + long text")
    # post_update("https://forums.kleientertainment.com/game-updates/dst/499972-r1765/")

    # # ######################################################################

    # print("Description test")
    # post_update("https://forums.kleientertainment.com/game-updates/dst/499819-r1764/")

    # # ######################################################################

    # print("Code Block Test")
    # post_update("https://forums.kleientertainment.com/game-updates/dst/528116-r1891/")

    # ######################################################################

    # print("Multiple rewardlink fetch test")
    # post_update("https://forums.kleientertainment.com/game-updates/dst/605310-r2186/", PostTag.MAJOR)
