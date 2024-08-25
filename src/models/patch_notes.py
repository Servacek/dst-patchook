import requests
import json
import re

from bs4 import BeautifulSoup, Tag, NavigableString

# Constants
SPOILER_CLASS_NAME = "ipsSpoiler"
SPOILER_HEADER_CLASS_NAME = "ipsSpoiler_header"
TITLE_CLASS_NAME = "ipsType_pageTitle"
EMBED_CLASS_NAME = "ipsEmbed_finishedLoading"

FORMAT_CHARS = [
    "*",
    "_",
    ">",
    "|",
    "~",
    "`",
    "-",
    "[",
    "]",
    "#"
]

DISCORD_MARKDOWN_HTML = {
    "strong": "**{}**",
    "b": "**{}**",
    "i": "*{}*",
    "u": "__{}__",
    "s": "~~{}~~",
    #"pre": "```{}```",
    "h1": "# {}",
    "h2": "## {}",
    "h3": "### {}",
    "small": "-# {}",
}

BLOCK_START_CHAR = "```"

# Used when translating tabs to spaces.
TAB_SIZE = 4
IDENT_LEVEL_SPACES = "  "

DEFAULT_FONT_SIZE = 13
DEFAULT_MARGIN_LEFT = 0

class PatchNotes:
    """
        Factory class for building nice formatted patchnotes from a string
    """

    notes: list[str]

    def __init__(self, obj: Tag):
        self.notes = self._build(obj)

    #######################
    ## Private
    #######################

    def _calc_identation_level(self, line: str) -> int:
        return line.count("\t\t")

    def _get_identation_prefix(self, identation_level: int, index: int = 0, ordered: bool = False) -> str:
        """
        Get the indentation prefix for a given indentation level.

        Args:
            identation_level (int): The indentation level.
            index (int, optional): The index of the item in the list. Defaults to 0.

        Returns:
            str: The indentation prefix.
        """

        # Support for ordered lists.
        if index and ordered:
            return f"{IDENT_LEVEL_SPACES * (identation_level - 1)}{index}. "

        # Discord now supports list items markdown!
        if identation_level > 0:
            return f"{IDENT_LEVEL_SPACES * (identation_level - 1)}- "

        return ""

    def _normalize_line(self, line):
        # Also replace non-break spaces with normal ones.
        return self._ddf(line.replace("\xa0", " ").replace("`", "ˋ"))

    def _apply_identation(self, tag: Tag):
        stack = [(tag, 0)]

        while stack:
            tag, depth = stack.pop()
            for child in tag.children:
                if isinstance(child, NavigableString):
                    child.replace_with(self._normalize_line(child))
                    continue

                if not isinstance(child, Tag):
                    continue

                if child.name == 'ul':
                    stack.append((child, depth + 1))
                    continue

                # Replace just the first Navigable string here because we want to leave the tags untouched.
                # TODO: Potencial support for "li" strings that start with a tag (e. g. <strong>)
                if child.name == 'li' and isinstance(child.contents[0], NavigableString):
                    child.contents[0].replace_with(
                        ("\t\t" * depth) + child.contents[0].lstrip())
                    continue

                stack.append((child, depth))

    def _normalize_obj(self, obj: Tag):  # -> Tag:
        # Remove the "Update Information" thing, it's always there so it's redundant.
        title = obj.find('h2', {'class': TITLE_CLASS_NAME})
        if title:
            title.decompose()

        self._apply_identation(obj)

        for block in obj.find_all("pre"):
            if block.string:
                block.string = BLOCK_START_CHAR + \
                    block.string.replace(
                        "\t", " " * TAB_SIZE) + BLOCK_START_CHAR

        # Remove all spoiler headers (the "Spoiler" text at the begining) from obj even nested
        for spoiler_header in obj.find_all('div', {'class': SPOILER_HEADER_CLASS_NAME}):
            spoiler_header.decompose()

        for spoiler in obj.find_all("div", {"class": SPOILER_CLASS_NAME}):
            # Got throw each line in the spoiler and add ">>> " to the beginning
            for line in spoiler.find_all(text=True):
                if line.strip():
                    line.replace_with(f"> {line.lstrip()}")

        # Find all spans where they sent custom font size
        for span in obj.find_all("span", style=lambda value: value and 'font-size' in value):
            # Find the font-size value using regex
            font_size_match = re.search(r'font-size:\s*(\d+)px', span["style"])
            if font_size_match:
                # Convert the matched value to an integer
                font_size = int(font_size_match.group(1))
                if font_size > DEFAULT_FONT_SIZE:
                    span.string = "## " + span.string + "\n"
                else:
                    span.string = "-# " + span.string + "\n"

        # Handle margin overrides
        for p in obj.find_all("p", style=lambda value: value and 'margin-left' in value):
            margin_left_march = re.search(r'margin-left:\s*(\d+)px', p["style"])
            if margin_left_march:
                margin_left = int(margin_left_march.group(1))
                if margin_left > DEFAULT_MARGIN_LEFT:
                    p.string = '\n'.join([
                        ("> " + line if line.strip() and not line.strip().startswith("> ") else line) for line in p.text.splitlines()
                    ])

        # TODO: Debug
        for embed in obj.find_all('iframe', {'class': EMBED_CLASS_NAME}):
            embed_link = embed.get("src")
            if not embed.string or not embed_link:
                continue

            embed_soup = BeautifulSoup(requests.get(
                embed_link).text, features='html.parser')
            hyperlink = embed_soup.find('div', {'class': 'ipsRichEmbed_header ipsAreaBackground_light ipsClearfix'}).find(
                'a', {'class': 'ipsRichEmbed_openItem'}).get("href")
            embed.string = f" {hyperlink}"

        for emoji in obj.find_all("img"):
            title = emoji.get("title")
            if title is not None:
                emoji.replace_with(title)

        for hyperlink in obj.find_all('a'):
            url = hyperlink.get('href')

            if hyperlink.string is None:
                if url and url.startswith("http"):
                    hyperlink.string = url.strip()
                continue

            if url and not hyperlink.string.strip().startswith("http"):
                hyperlink.string.replace_with(f"{' ' if hyperlink.string.startswith(' ') else ''}[{hyperlink.string}]({url})")
            else:
                hyperlink.string.replace_with(hyperlink.string.strip())

        for line_breaker in obj.find_all('br'):
            line_breaker.replace_with("\n")

    def _ddf(self, string: str) -> str:
        result = string
        for char in FORMAT_CHARS:
            result = result.replace(char, "\\" + char)

        return result

    def _apply_markdown(self, obj: Tag):  # -> Tag:
        for tag in obj.find_all(DISCORD_MARKDOWN_HTML.keys()):
            template = DISCORD_MARKDOWN_HTML.get(tag.name)
            if tag.text is None or template is None:
                continue

            string = ""
            for line in tag.text.splitlines(True):
                # No markdown for links, let discord handle that.
                if line.strip() and not line.startswith("http"):
                    # We were stripping the line, so give it at least the trailling space.
                    string += template.format(line)
                else:
                    string += line

            tag.string = string

    def _build(self, obj: Tag) -> list[str]:
        newline: bool = False
        last_ident: int = 0
        result: list[str] = []
        block: bool = False
        last_text_index: int = 0

        self._normalize_obj(obj)
        self._apply_markdown(obj)

        lines = obj.get_text().splitlines(True)
        for line in lines:
            if line.strip("\n").startswith(BLOCK_START_CHAR):
                block = not block

            if block:
                result.append(line)
                continue

            # Ensure that every line has a newline break.
            # Also remove all the unnecessary empty characters.
            stripped = line.strip() + ("\n" if line.strip(" \t\r").endswith("\n") else "")
            if not stripped:
                continue # Skip blank lines

            last_line = result and result[last_text_index] or None
            if stripped == "\n":
                # Skip the leading new lines since they will be stripped anyway.
                if newline is False and result and last_ident == 0 and not stripped.startswith("## "):
                    newline = True
                    result.append("\n")

                continue

            identation_level = self._calc_identation_level(line)
            prefix = self._get_identation_prefix(identation_level)

            # Some devs use the start for list items...
            if stripped.startswith("\\*"):
                prefix = ""

            # For patch note headers
            # Remove the aditional space between the header and first list item.
            if result and (identation_level > 0 or (
                identation_level == 0 and last_line and last_line.lstrip().startswith("*") and
                last_line.rstrip().endswith("*")
            )):
                if result[len(result) - 1] == "\n" and last_ident == 0:
                    result.pop()

                # Make the header bold if it's not already.
                if last_ident == 0 and last_line and not "**" in last_line and len(last_line) < 64:
                    if last_text_index - 1 >= 0 and result[last_text_index - 1] != "\n":
                        result.insert(last_text_index, "\n")
                        last_text_index += 1

                    result[last_text_index] = "**" + last_line.rstrip() + "**\n"

            # For description headers
            if not stripped.startswith("**") and identation_level == 0 and last_line and last_line.lstrip().startswith("*"):
                if result[len(result) - 1] == "\n" and len(stripped) > 64 and last_line and len(last_line) < 64:
                    result.pop()

            # Make sure that the headers are one line behind descriptions.
            if identation_level == 0 and last_ident > 0 and not stripped.startswith("\n"):
                result.append("\n")

            result.append(prefix + stripped)
            newline = False
            last_ident = identation_level
            last_text_index = len(result) - 1

        return result
