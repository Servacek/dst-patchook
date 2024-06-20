from json import loads as json_loads
from bs4 import BeautifulSoup
from models import Author, PatchNotes
from re import search, findall, compile
from requests import get
from urllib.parse import urlparse

from icons import Icons

SECTION_CLASS_NAME = "ipsType_richText ipsType_normal"
SPOILER_CLASS_NAME = "ipsSpoiler"
TITLE_CLASS_NAME = "ipsType_pageTitle"
EMBED_CLASS_NAME = "ipsEmbed_finishedLoading"
BADGE_CLASS_NAME = "ipsBadge ipsBadge_icon ipsBadge_small ipsBadge_positive"
VERSION_CLASS_NAME = "ipsType_sectionHead ipsType_break"

YT_URL_PATTERN = r"(?:(?:https?:\/\/)?(?:youtu\.be\/|(?:www\.|m)\.?youtube(?:-nocookie)?\.com\/(?:watch|v|embed)(?:\.php)?(?:\?.*v=|\/)))([a-zA-Z0-9\_-]+)(?:\?.*)?"
#YT_URL_PATTERN = "src"
#YT_URL_PATTERN = "^(?:https?:)?\/\/?(?:www|m)\.?(?:youtube(-nocookie)?\.com|youtu.be)\/(?:[\w\-]+\?v=|embed\/|v\/)?([\w\-]+)\S+?$"
YT_VIDEO_TEMPLATE = "https://www.youtube.com/watch?v={}"
YT_API_TEMPLATE = "https://noembed.com/embed?url={}"
KLEI_YT_CHANNEL_URL = "https://www.youtube.com/@kleient"
YT_VIDEO_THUMBNAIL_TEMPLATE = "https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
FORUM_DISCUSSION_URL_PATTERN = r'https:\/\/forums.kleientertainment.com\/forums\/topic\/[^" \/]+'

# youtube_regex = (
#     r'(https?://)?(www\.)?'
#     '(youtube|youtu|youtube-nocookie)\.(com|be)/'
#     '(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})')

EMBED_TITLE = "[Game Update] - {} {}"
HYPERLINK = "[{text}]({url})"

COLOR_ORANGE = 15105570     # For releases
COLOR_BLUE  = 3447003       # For betas

MAX_DESCRIPTION_LENGHT = 4050
MAX_FIELD_VALUE_LEN = 1024
MAX_FIELDS = 25
MAX_TOTAL_CHARACTERS = 6000
MAX_CONTENT_LEN = MAX_TOTAL_CHARACTERS - 250 # Reserve for title, author and footer

REWARD_LINK_PATTERN = r'(https:\/\/accounts.klei.com\/link\/[^" \/\)]+)'

GAME_NAME_NORMALIZED = "don't starve"

# Helper functions

def get_video_info(url) -> dict:
    return get(YT_API_TEMPLATE.format(url)).json()

##################

class PatchTag:
    HOTFIX  = "hotfix"
    MAJOR   = "major"
    RELEASE = "release"
    BETA    = "beta"


TITLE_TAGS = {
    PatchTag.BETA:     "(Beta)",
    PatchTag.RELEASE:  "(Release)",
}

##################

"""
    Represents an game update patch
"""
class Patch:

    version: int
    url: str
    forum_url: str = ""
    video_url: str = ""
    hotfix: bool
    beta: bool
    soup: BeautifulSoup
    title: str
    json: dict
    author: Author
    notes: PatchNotes
    spoilers_removed: bool = False
    was_built: bool = False

    thumbnail_url: str = None
    forum_url: str = None
    video_url: str = None

    def __init__(self, *, hotfix: bool, beta: bool, version: int, url: str, soup: BeautifulSoup):
        self.version = version
        self.url = url
        self.hotfix = hotfix
        self.beta = beta
        self.soup = soup

        self.title = EMBED_TITLE.format(self.version, self._get_title_tag())
        self.id = url.strip("/").split("/")[-1]

        self._build(soup)

        article = soup.find('article', {
            'class': 'ipsContained ipsSpacer_top'
        })

        self.forum_url = self._get_forum_page(article)
        if not self.has_forum() and self.is_major():
            print("Couldn't fetch forum url for major version", self.version)

        self.discussion_url = None
        matches = article.findAll('a', href=compile(FORUM_DISCUSSION_URL_PATTERN))
        if matches:
            self.discussion_url = matches[-1].get("href")

        self.video_url, self.thumbnail_url = self._get_trailer()
        if self.thumbnail_url is None:
            # We were not able to fetch the thumbnail from the video, so try to find
            # the first image in the post and use that instead.
            self.thumbnail_url = self._get_thumbnail(article)

    #################################

    def _build(self, soup: BeautifulSoup) -> None:
        if self.was_built:
            return print("[Warn] Attempted to build an already built patch!")

        self.soup: BeautifulSoup = soup

        obj = soup.find('section', {'class': SECTION_CLASS_NAME})

        self.notes = PatchNotes(self.url, obj)
        self.json = json_loads(
            "".join(soup.find("script", {"type":"application/ld+json"}).contents)
        )
        self.author = Author(self.json['author'])

        self.release_date = self.json['datePublished']

        self.rewardlinks = findall(REWARD_LINK_PATTERN, soup.text)

        self.was_built = True

    def _get_trailer(self) -> str:
        video_match = search(YT_URL_PATTERN, str(self.soup))
        video_id    = video_match and video_match[1] or None
        video_url   = YT_VIDEO_TEMPLATE.format(video_id) if video_id else ""
        thumbnail_url = None

        if len(video_url) > 0:
            video_info = get_video_info(video_url)
            thumbnail_url = YT_VIDEO_THUMBNAIL_TEMPLATE.format(video_id = video_id)

            # Make sure the video is from Klei
            if video_info.get("author_url") != KLEI_YT_CHANNEL_URL:
                return "", thumbnail_url

            # Check if the video is about don't starve
            if not GAME_NAME_NORMALIZED in video_info['title'].lower():
                return "", thumbnail_url

        return video_url, thumbnail_url

    def _get_thumbnail(self, article) -> str:
        thumbnail = article.find('img')
        thumbnail_url = thumbnail and thumbnail.get("src") or None

        if not thumbnail_url:
            return

        return urlparse(thumbnail_url, scheme='https').geturl()

    def _get_forum_page(self, article) -> str:
        article_urls = article.find_all('a')
        if article_urls and len(article_urls) < 2:
            return ""

        return article_urls[-2].get('href') or ""

    def _get_title_tag(self) -> str:
        if self.is_beta():
            return TITLE_TAGS[PatchTag.BETA]

        if self.is_major():
            return TITLE_TAGS['release']

        return ""

    def _get_link_list(self) -> list[dict[str, str]]:
        """Returns a dictionary with the text of the hyperlink as key and the link as value."""

        hyperlinks = [
            {"url": self.video_url, "text": "Watch Trailer", "icon": Icons.YOUTUBE} if self.has_trailer() else None,
            {"url": self.discussion_url, "text": "Join Discussion", "icon": Icons.FORUM} if self.discussion_url else None,
        ]
        for rewardlink in self.rewardlinks:
            hyperlinks.append({"url": rewardlink, "text": "Klei Points/Spools", "icon": Icons.POINTS})

        return [hyperlink for hyperlink in hyperlinks if hyperlink is not None]

    #################################

    def is_beta(self) -> bool:
        return self.beta

    def is_release(self) -> bool:
        return not self.beta

    def is_hotfix(self) -> bool:
        return self.hotfix

    def is_major(self) -> bool:
        return not self.hotfix

    def has_trailer(self) -> bool:
        return isinstance(self.video_url, str) and len(self.video_url) > 0

    def has_forum(self) -> bool:
        return isinstance(self.forum_url, str) and len(self.forum_url) > 0

    def has_thumbnail(self) -> bool:
        return isinstance(self.thumbnail_url, str) and len(self.thumbnail_url) > 0

    def get_tags(self) -> list[PatchTag]:
        tags = [
            PatchTag.MAJOR if self.is_major() else None,
            PatchTag.HOTFIX if self.is_hotfix() else None,
            PatchTag.BETA if self.is_beta() else None,
            PatchTag.RELEASE if self.is_release() else None
        ]
        return [tag for tag in tags if tag is not None]

    #################################

    def get_links_header(self) -> str:
        header = ""
        for hyperlink in self._get_link_list():
            header += "### " + hyperlink.get("icon", "-") + " " + HYPERLINK.format(
                text = hyperlink["text"],
                url  = hyperlink["url"]
            ) + "\n"

        # Show only the embed of the url
        return "# Links\n" + header if header else ""

    def get_link_buttons(self):
        buttons = []
        for hyperlink in self._get_link_list():
            # <:NAME:ID>
            animated, emoji_name, emoji_id = hyperlink["icon"].strip("<>").split(":")
            buttons.append({
                "type": 2, # Button
                "label": hyperlink["text"],
                "style": 5, # Link Button
                "url": hyperlink["url"],
                "emoji": {
                    "id": int(emoji_id),
                    "name": emoji_name,
                    "animated": animated == "a",
                }
            })

        return buttons

    def to_embed(self) -> dict:
        if not self.was_built:
            return None

        description: str = ""
        fields = []
        field_index = -1
        total_len = 0

        for note in self.notes.notes:
            if (total_len + len(note)) >= MAX_CONTENT_LEN:
                if fields:
                    fields[field_index]["value"] += "..."
                else:
                    description += "..."

                break

            if (len(description) + len(note)) < MAX_DESCRIPTION_LENGHT and not fields:
                description += note
                total_len += len(note)
                continue

            # We have found a header. Try to add it to a separate field.
            if note.strip("\n").startswith("**") and len(fields) < MAX_FIELDS:
                note = note.strip()[2:-2]
                fields.append({"name": note, "value": ""})
                field_index += 1
                total_len += len(note)
                continue

            # Add a field with a an empty title to continue filling the overflown description.
            if not fields or len(fields[field_index]["value"]) + len(note) >= MAX_FIELD_VALUE_LEN:
                fields.append({"name": "", "value": ""})
                field_index += 1

            # The description is full, start filling out the fields.
            fields[field_index]["value"] += note
            total_len += len(note)

        return {
            "title": self.title,
            "url": self.url,
            "timestamp": self.release_date,
            "color": COLOR_BLUE if self.beta else COLOR_ORANGE,
            "author": self.author.to_embed(),
            "fields": fields,
            "description": description,
            "footer": {
                "text": "" if self.is_major else "A beta is available for this version." if self.beta else "This is a hotfix release.",
            },
        }

    def to_dict_for(self) -> dict:
        result = {}

        embed = self.to_embed()
        if embed is not None:
            if self.has_thumbnail():
                # Set it as image instead of thumbnail so its bigger.
                embed["image"] = {
                    "url": self.thumbnail_url,
                }

            result['embeds'] = [embed]

        return result
