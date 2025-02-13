from json import loads as json_loads
from bs4 import BeautifulSoup
from models import PatchNotes
from re import search, findall, compile, sub
from requests import get
from urllib.parse import urlparse

from dateutil import parser

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
FORUM_DISCUSSION_URL_PATTERN = compile(r'https:\/\/forums.kleientertainment.com\/forums\/topic\/[^" \/]+\/?')
KLEI_BUG_TRACKER_URL = "https://forums.kleientertainment.com/klei-bug-tracker/" #compile(r'https:\/\/forums.kleientertainment.com\/klei-bug-tracker\/[^" \/]+\/?\"')
FULL_UPDATE_URL_PATTERN  = '(https:\/\/forums.kleientertainment.com\/game-updates\/.+\/{}-r\d+\/?)'
KLEI_FORUMS_URL = "https://forums.kleientertainment.com/forums/"
KLEI_AMBASSADOR_LIST = "https://forums.kleientertainment.com/ambassador-list/"
KLEI_TWITCH_CHANNEL = "https://www.twitch.tv/kleientertainment"
TWITCH_DROPS_ARTICLE_URL = "https://support.klei.com/hc/en-us/articles/360029881771-Twitch-tv-Drops"
TWITCH_DROP_ANIM_URL = r'(http[s]?:\/\/kleiforums\.s3\.amazonaws\.com\/drops\/post\/.+\.html)'
TWITCH_DROP_IMAGE_URL_PATTERN = r'(https:\/\/cdn\.forums\.klei\.com\/drops\/image\/.+_item\.jpg)'
BETA_BRANCH_OPTIN_POST_URL = "https://forums.kleientertainment.com/forums/topic/106156-how-to-opt-in-to-the-beta-branch-for-dont-starve-together/"

# youtube_regex = (
#     r'(https?://)?(www\.)?'
#     '(youtube|youtu|youtube-nocookie)\.(com|be)/'
#     '(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})')

EMBED_TITLE = "[Game Update] - {} {}"
HYPERLINK = "[{text}]({url})"

COLOR_ORANGE    = 15105570
COLOR_BLUE      = 3447003
COLOR_GREEN     = 5294200
COLOR_PURPLE    = 6570405 # Inspired by Twitch.tv
COLOR_BROWN     = 8999209

DEFAULT_COLOR = COLOR_ORANGE
DEFAULT_TAG_PRIORITY = 0

# PREFIX CONSTANTS RETRIEVED FROM THE DISCORD API WITH "DISCORD_"
MAX_DESCRIPTION_LENGHT = 4050
DISCORD_MAX_FIELD_VALUE_LEN = 1024
DISCORD_MAX_FIELDS = 25
DISCORD_MAX_TOTAL_CHARACTERS = 6000
MAX_CONTENT_LEN = DISCORD_MAX_TOTAL_CHARACTERS - 250 # Reserve for title, author and footer

REWARD_LINK_PATTERN = r'(http[s]?:\/\/accounts.klei.com\/link\/[^" \:\?\@\&\#\[\>\)\(\]\<\n\t\/]+)\"'

GAME_NAME_NORMALIZED = "don't starve"

# Helper functions

def get_video_info(url) -> dict:
    return get(YT_API_TEMPLATE.format(url)).json()


def get_embed_total_length(embed):
    # TODO: Figure out why this counts only ~4500 characters
    # but it fails saying the embed has reached the 6000 character limit.

    # Additionally, the combined sum of characters in all title, description, field.name,
    # field.value, footer.text, and author.name fields across all embeds attached to a message
    # must not exceed 6000 characters.
    total_embed_length = 0
    total_embed_length += len(embed.get("description", ""))
    total_embed_length += len(embed.get("title", ""))
    total_embed_length += len(embed.get("author", {}).get("name", ""))
    total_embed_length += len(embed.get("footer", {}).get("text", ""))
    for field_name, field_value in embed.get("fields", []):
        total_embed_length += len(field_name) + len(field_value)

    return total_embed_length

##################

class _PTag:
    id: str
    priority: int = DEFAULT_TAG_PRIORITY
    data: dict

    def __init__(self, id, priority=DEFAULT_TAG_PRIORITY, **kwargs):
        self.id = id
        self.priority = priority
        self.data = dict(kwargs)

    def __repr__(self): return self.id
    def __str__(self): return self.id
    def __hash__(self): return hash(self.id)
    def __eq__(self, other): return self.id == other
    def __ne__(self, other): return self.id != other
    def __lt__(self, other): return self.priority < other
    def __le__(self, other): return self.priority <= other
    def __gt__(self, other): return self.priority > other
    def __ge__(self, other): return self.priority >= other
    def __contains__(self, other): return other in self.data

    def get(self, name: str, default=None):
        return self.data.get(name, default)

class PostTag: # The default category is "announcement"
    UPDATE      = _PTag("update", color=COLOR_ORANGE) # {"id": "update", "color": COLOR_ORANGE}
    HOTFIX      = _PTag("hotfix", color=COLOR_BROWN, priority=2,
        footer_text="This is a hotfix release",
        footer_icon_url="https://cdn.discordapp.com/attachments/1066442901380403333/1339626180810244096/fire.png"
    )
    MAJOR       = _PTag("major", color=COLOR_ORANGE, priority=2)
    RELEASE     = _PTag("release", title_tag="(Release)")
    BETA        = _PTag("beta", color=COLOR_BLUE, title_tag="(Beta)", priority=3,
        footer_text="A beta is available for this version",
        footer_icon_url="https://cdn.discordapp.com/attachments/1066442901380403333/1339626219091791963/salt.png"
    )
    FORUM_POST  = _PTag("forum")
    TWITCH_DROP = _PTag("twitch_drop", color=COLOR_PURPLE, priority=2, buttons=[
        {"url": KLEI_AMBASSADOR_LIST, "text": "Klei Ambassadors", "icon": Icons.AMBASSADORS},
    ])
    ROADMAP     = _PTag("roadmap", color=COLOR_GREEN, priority=2)
    DEV_STREAM  = _PTag("dev_stream", color=COLOR_PURPLE, priority=2, buttons=[
        {"url": KLEI_TWITCH_CHANNEL, "text": "Klei Twitch Channel", "icon": Icons.TWITCH},
    ])
    TEASER      = _PTag("teaser", priority=2)
    TRAILER     = _PTag("trailer", priority=2)
    REWARDLINKS = _PTag("rewardlinks")
    ANNOUNCEMENT = _PTag("announcement")
    INTERMISSION = _PTag("intermission")

PostTag.ALL = [f for f in PostTag.__dict__.values() if isinstance(f, _PTag)]
PostTag.ALL_IDS = [tag.id for tag in PostTag.ALL]
PostTag.TAG_BY_ID = {tag.id: tag for tag in PostTag.ALL}

##################

"""
    Represents a post
"""
class Post:

    url: str
    video_url: str = ""
    soup: BeautifulSoup
    title: str
    json: dict
    tags: set[_PTag]
    version: int = float("inf")
    author: dict[str, str] = None
    publish_date: str = ""
    discussion_url: str = None
    full_update_url: str = None
    release_id: int = None # Speacial field for updates (eqaul to the rowId in the url)
    notes: PatchNotes

    thumbnail_url: str = None

    publish_timestamp: int = None

    DEFAULT_AUTHOR_NAME = "Klei Entertainment"
    DEFAULT_AUTHOR_ICON_URL = "https://cdn.discordapp.com/attachments/1066442901380403333/1334850877831516211/images.png"
    DEFAULT_AUTHOR_URL = "https://forums.kleientertainment.com/"

    def __init__(self, *tags, url: str, soup: BeautifulSoup, source_url: str=None, version: int=None) -> None:
        self.tags = set([tag for tag in tags if isinstance(tag, _PTag)]) # This has to be defined here so it is unique for each post.

        self.url = url
        self.source_url = source_url
        self.soup = soup

        # <meta property="og:title" content="DST Update - Depths of Duplicity Now Live!">
        title_element = self.soup.find("h1", {"class": "ipsType_pageTitle ipsType_largeTitle ipsType_break"})
        self.title = title_element and title_element.text or None
        if self.title is None:
            self.title = self.soup.find("meta", property="og:title").get("content") if self.soup else ""

        obj = self.soup.find('section', {'class': SECTION_CLASS_NAME}) if self.soup else None
        # TODO: This could be potentially expanded here if we want more text.
        #obj = self.soup.find('article') if self.soup else None
        if not obj:
            obj = self.soup.find("div", {"data-role": "commentContent"}) if self.soup else None

        self.notes = PatchNotes(obj.__copy__()) if obj else None # using a copy so it doesn't overwrite the original soup
        if self.soup:
            self.json = json_loads("".join(self.soup.find("script", {"type":"application/ld+json"}).contents))

            author_data = self.json.get("author", None)
            author_name = author_data.get("name", "") if author_data else None # This is a required field by the discord API
            self.author = {
                "name":     author_name if author_name else Post.DEFAULT_AUTHOR_NAME,
                "icon_url": urlparse(author_data['image'], scheme='https').geturl() if author_name else Post.DEFAULT_AUTHOR_ICON_URL,
                "url":      urlparse(author_data['url'], scheme='https').geturl() if author_name else Post.DEFAULT_AUTHOR_URL,
            }

            self.publish_date = self.json.get("datePublished", "")

        try:
            self.publish_timestamp = int(parser.parse(self.publish_date).timestamp())
        except ValueError or TypeError as e:
            print(f"[Error] Failed to parse 'datePublished' for post {self.version}")
            print(f"[Error] {e}")
            self.publish_timestamp = None

        self.version = version or self.publish_timestamp or self.version
        self.rewardlinks = set(findall(REWARD_LINK_PATTERN, str(self.soup))) if self.soup else []
        if self.rewardlinks:
            self.add_tag(PostTag.REWARDLINKS)

        article = None if not self.soup else (
            self.soup.find("div", {"data-role": "commentContent"}) or self.soup.find('article') # Get the first article
        )

        # This is a bit more specific since the URL could match anything.
        self.discussion_url = None
        matches = article.find_all('a', href=FORUM_DISCUSSION_URL_PATTERN) if article else None
        #print("\n".join(filter(None, [x.get("href") for x in article.find_all("a", recursive=False) if x.text == "Discussion Topic"])) if article else "")
        if matches:
            self.discussion_url = matches[-1].get("href")
        if not self.has_tag(PostTag.UPDATE):
            self.discussion_url = self.url

        self.full_update_url = None
        match = search(compile(FULL_UPDATE_URL_PATTERN.format(self.version)), str(self.soup)) if self.soup else None
        if match:
            self.full_update_url = match.group()

        self.video_url, self.thumbnail_url = self._get_trailer()
        if self.thumbnail_url is None and article:
            # We were not able to fetch the thumbnail from the video, so try to find
            # the first image in the post and use that instead.
            self.thumbnail_url = self._get_thumbnail(article)

        twitch_drop_anim_html_url = search(TWITCH_DROP_ANIM_URL, str(self.soup)) if self.soup else None
        if twitch_drop_anim_html_url is not None:
            self.add_tag(PostTag.TWITCH_DROP)

            if twitch_drop_anim_html_url:
                page = get(twitch_drop_anim_html_url.group())
                if page.text is not None:
                    self.thumbnail_url = search(TWITCH_DROP_IMAGE_URL_PATTERN, page.text).group() or self.thumbnail_url

        if not self.has_tag(PostTag.UPDATE):
            self.add_tag(PostTag.ANNOUNCEMENT)

        if self.has_tag(PostTag.UPDATE) and not self.has_tag(PostTag.HOTFIX) and not self.has_tag(PostTag.BETA):
            self.add_tag(PostTag.RELEASE)

        if "intermission" in str(self.title).lower():
            self.add_tag(PostTag.INTERMISSION)

        if self.has_tag(PostTag.ANNOUNCEMENT) and KLEI_TWITCH_CHANNEL in str(article): self.add_tag(PostTag.DEV_STREAM)
        if self.has_tag(PostTag.ANNOUNCEMENT) and "roadmap" in self.title.lower(): self.add_tag(PostTag.ROADMAP)

        if self.has_tag(PostTag.ANNOUNCEMENT) and "coming soon" in self.title.lower() or "coming next week" in self.title.lower():
            self.add_tag(PostTag.TEASER)

        if isinstance(self.video_url, str) and len(self.video_url) > 0:
            self.add_tag(PostTag.TRAILER)

    def __str__(self) -> str:
        return f"<Post url={self.url} version={self.version}>"

    #################################

    def _get_trailer(self) -> str:
        video_match = search(YT_URL_PATTERN, str(self.soup or ""))
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
        thumbnail = article.find('img', {'class': 'ipsImage ipsImage_thumbnailed'})
        thumbnail_url = thumbnail and thumbnail.get("src") or None
        if not thumbnail_url:
            image = article.find('img')
            thumbnail_url = image.get("src") if image else None
        # Get only first OR last image?
        # if thumbnail is not None and thumbnail.parent:
        #     for sibling in thumbnail.parent.previous_siblings:
        #         if sibling.name == 'p' and sibling.text:
        #             break
        #     else:
        #         thumbnail = None

        if not thumbnail_url or not thumbnail_url.lower().endswith(('.png', '.gif', '.jpg', '.jpeg', '.webp')):
            return

        return urlparse(thumbnail_url, scheme='https').geturl()

    def _get_tag_field(self, tag_field: str, default=None):
        highest_priority_yet = DEFAULT_TAG_PRIORITY
        value_yet = None
        for tag in self.tags:
            if tag_field in tag and (
                value_yet is None or tag.priority > highest_priority_yet
            ):
                value_yet = tag.get(tag_field, value_yet)
                highest_priority_yet = tag.priority

        return default if value_yet is None else value_yet

    def _get_link_list(self) -> list[dict[str, str]]:
        """Returns a dictionary with the text of the hyperlink as key and the link as value."""

        hyperlinks = [ # Sorted by frequency of occurrence
            # Maybe only one of those would be enough?
            {"url": self.discussion_url or KLEI_FORUMS_URL, "text": "Join Discussion", "icon": Icons.FORUM},
            {"url": self.full_update_url, "text": "View Full Update", "icon": Icons.CHANGELOG} if self.full_update_url and self.has_tag(PostTag.UPDATE) else None,
            # This button is just uneccessary
            #{"url": KLEI_BUG_TRACKER_URL, "text": "Klei Bug Tracker", "icon": Icons.BUG_TRACKER} if self.has_tag(PostTag.UPDATE) else None,§
            {"url": BETA_BRANCH_OPTIN_POST_URL, "text": "Opt-In the Beta Branch", "icon": Icons.BETA} if self.has_tag(PostTag.BETA) and self.has_tag(PostTag.UPDATE) else None,
            {"url": self.video_url, "text": "Watch Trailer", "icon": Icons.YOUTUBE} if isinstance(self.video_url, str) and len(self.video_url) > 0 else None,
        ]
        for rewardlink in self.rewardlinks:
            hyperlinks.append({"url": rewardlink, "text": "Klei Points/Spools", "icon": Icons.POINTS})

        for tag in self.tags:
            hyperlinks.extend(tag.get("buttons", []))

        return [hyperlink for hyperlink in hyperlinks if hyperlink is not None]

    #################################

    def get_tags(self) -> set[_PTag]:
        return set(self.tags) # Returns a copy so this is read-only

    def has_tag(self, tag: _PTag) -> None:
        return tag in self.tags if isinstance(tag, _PTag) else any(t.id == tag for t in self.tags)

    def add_tag(self, tag: _PTag) -> None:
        self.tags.add(tag)

    def add_tags(self, *tags: _PTag) -> "Post":
        self.tags.update(tags)
        return self

    def meets_tag_rule(self, tag_rule: str) -> bool:
        rules = tag_rule.split() if tag_rule else []
        if not rules:
            return True # What is not prohibited is allowed, right?

        tags_required, tags_prohibited, tags_optional = [], [], []
        for tagid in rules:
            tagid = tagid.strip()
            tag_name = tagid.strip("!").strip("?")
            if not tag_name in PostTag.ALL_IDS:
                print("[Warn] Post tag", tag_name, "is not valid!")
                continue

            if tagid.startswith("!") or tagid.endswith("!"):
                tags_prohibited.append(tag_name)
            elif tagid.startswith("?") or tagid.endswith("?"):
                tags_optional.append(tag_name)
            else:
                tags_required.append(tag_name)

        return (
            all(self.has_tag(tagid) for tagid in tags_required) and # All required tags!
            not (any(self.has_tag(tagid) for tagid in tags_prohibited) and tags_prohibited)# and # No prohibited tags!
            #all((tag.id in tags_required or tag.id in tags_optional) for tag in self.tags) # No redundant tags!
        )

    #################################

    def get_desc_footer(self):
        return (
            "-# You can join in the [Discussion Topic](<{}>) here.\n"
            "-# If you run into a bug, please visit the [Klei Bug Tracker](<{}>)."
        ).format(self.discussion_url or KLEI_FORUMS_URL, KLEI_BUG_TRACKER_URL) \
            if (self.has_tag(PostTag.UPDATE)) else ""

    def get_links_header(self) -> str:
        header = ""
        for hyperlink in self._get_link_list():
            header += "### " + hyperlink.get("icon", "-") + " " + HYPERLINK.format(
                text = hyperlink["text"],
                url  = hyperlink["url"]
            ) + "\n"

        # Show only the embed of the url
        return "# Links\n" + header if header else ""

    def get_link_buttons(self, link_list: dict[str, str]=None) -> dict[str, str]:
        if link_list is None:
            link_list = self._get_link_list()

        buttons = []
        for hyperlink in link_list:
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

    def to_embed(self, config={}) -> dict:
        description: str = ""
        fields = []
        field_index = -1
        has_footer = config.get("footer") is True
        # Keep one field for the footer!
        max_fields = DISCORD_MAX_FIELDS - 1 if has_footer else DISCORD_MAX_FIELDS

        embed = {
            "title": EMBED_TITLE.format(self.title, self._get_tag_field("title_tag", "")) if self.has_tag(PostTag.UPDATE) and self.title.isdigit() else self.title,
            "url": self.url,
            "color": self._get_tag_field("color", DEFAULT_COLOR),
            "author": self.author,
            "footer": { "text": self._get_tag_field("footer_text", ""), "icon_url": self._get_tag_field("footer_icon_url")},
        }

        desc_footer = self.get_desc_footer()
        total_len = get_embed_total_length(embed) + len(desc_footer)
        for note in (self.notes.notes if self.notes else []):
            if (total_len + len(note)) >= min(config.get("max_patch_length", MAX_CONTENT_LEN), MAX_CONTENT_LEN):
                if fields:
                    fields[field_index]["value"] += "..."
                else:
                    description += "..."

                break

            # If description is free, add it there prioritized.
            if (len(description) + len(note)) < MAX_DESCRIPTION_LENGHT and not fields:
                description += note
                total_len += len(note)
                continue

            # Fields do not support headers.
            note = sub(r"#+", r"\n", note)

            # We have found a header. Try to add it to a separate field.
            # if note.strip("\n").startswith("**") and len(fields) < max_fields:
            #     note = note.strip()[2:-2]
            #     fields.append({"name": note, "value": ""})
            #     field_index += 1
            #     total_len += len(note)
            #     continue

            # Add a field with a an empty title to continue filling the overflown description.
            if not fields or len(fields[field_index]["value"]) + len(note) >= DISCORD_MAX_FIELD_VALUE_LEN:
                fields.append({"name": "", "value": ""})
                field_index += 1

            # The description is full, start filling out the fields.
            fields[field_index]["value"] += note
            total_len += len(note)

        if has_footer and len(fields) < DISCORD_MAX_FIELDS:
            fields.append({
                "name": "",
                "value": self.get_desc_footer()
            })

        embed["description"] = description
        embed["fields"] = fields

        if self.publish_date is not None:
            embed["timestamp"] = self.publish_date

        if isinstance(self.thumbnail_url, str) and len(self.thumbnail_url) > 0:
            # Set it as image instead of thumbnail so its bigger.
            embed["image"] = { "url": self.thumbnail_url } # Set it as image instead of thumbnail so its bigger.

        return embed

    def to_dict(self, config={}) -> dict:
        return {"embeds": [self.to_embed(config)]}
