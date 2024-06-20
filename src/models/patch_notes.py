import requests
import json

from bs4 import BeautifulSoup, Tag, NavigableString

# Constants
PATH_CLASS_NAME = "ipsContained ipsSpacer_top"
SPOILER_CLASS_NAME = "ipsSpoiler"
TITLE_CLASS_NAME = "ipsType_pageTitle"
EMBED_CLASS_NAME = "ipsEmbed_finishedLoading"
BADGE_CLASS_NAME = "ipsBadge ipsBadge_icon ipsBadge_small ipsBadge_positive"
VERSION_CLASS_NAME = "ipsType_sectionHead ipsType_break"

CROPPED_MESSAGE = "Note: This post reached the discord message lenght limit so it was cropped...\nFull post can be found [here]({})."

DESCRIPTION_LEN_LIMIT = (4000 - len(CROPPED_MESSAGE))

FORMAT_CHARS = [
    "*",
    "_",
    ">",
    "|",
    "~",
    "`",
]

DISCORD_MARKDOWN_HTML = {
    "strong": "**{}**",
    "b": "**{}**",
    "i": "*{}*",
    "u": "__{}__",
    "s": "~~{}~~",
}

BLOCK_START_CHAR = "```"

TAB_SIZE = 4

IDENT_CHARS = {
    1: "• ",
    2: "◦ ",
    3: "⬝ ",
}

class LineTypes:

    DEFAULT         = "default"
    IDENTED         = "idented"
    DOUBLE_IDENTED  = "double_idented"
    UNIDENTED       = "unidented"
    BLANK           = "blank"
    SEPARATOR       = "separator"

"""
    Factory class for building nice formatted patchnotes from a string
"""
class PatchNotes:

    url: str
    notes: list[str]

    def __init__(self, url: str, obj: Tag):
        self.url = url
        self.notes = self._build(obj)

    def __str__(self):
        return "".join(self.notes)

    def __len__(self):
        return len(str(self))

    #######################
    ## Private
    #######################

    def _remove_blank(self, line: str, spaces=False) -> str:
        table = {chr(10): '', chr(9): '', ' ': ''} if spaces else {chr(10): '', chr(9): ''}
        return line.translate(line.maketrans(table))

    def _get_identation_level(self, line: str) -> int:
        return line.count("\t\t")

    def _is_idented(self, line: str) -> bool:
        for char in IDENT_CHARS.values():
            if line.startswith(char):
                return True

        return line.startswith("\t\t") or line.startswith("* ")

    def _get_identation_prefix(self, identation_level: int) -> str:
        if identation_level > 0:
            return f"{'  ' * (identation_level - 1)}- " # Discord now supports list items markdown!
            #return IDENT_CHARS.get(identation_level) or "⬝ "

        return ""

    def _calc_identation_spacing(self, identation_level: int) -> str:
        if identation_level > 1:
            return ' ' * (identation_level - 2)#'> ' + ('⠀' * (identation_level - 2))

        return ''

    def _normalize_line(self, line):
        # Also replace non-break spaces with normal ones.
        return self._ddf(line.replace("\xa0", " "))

    def _get_line_type(self, identation_level: int) -> str:
        # in most cases paraghraps are used for category separators or descriptions

        if identation_level >= 2: # Special patch line
            return LineTypes.IDENTED

        if identation_level == 1: # Default patch line
            return LineTypes.DEFAULT

        return LineTypes.UNIDENTED

    # TODO Count identation level using the ul tags.
    def _count_identation_for(self, ul, level: int = 1):
        if not ul:
            return 0

        parent = ul.find_parent("ul")
        if parent:
            return self._count_identation_for(parent, level=level+1)

        return level

    def _all_children(self, tag: Tag):
        # Generator function to traverse all tags using Breadth-First Search (BFS)
        queue = [tag]

        while queue:
            tag = queue.pop()
            yield tag

            if not isinstance(tag, Tag):
                continue

            # Add the immediate child elements to the queue
            for child in tag.children:
                queue.append(child)

    def _apply_identation(self, tag: Tag):
        stack = [(tag, 0)]
        depth = 0

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
                    child.contents[0].replace_with(("\t\t" * depth) + child.contents[0].lstrip())
                    continue

                stack.append((child, depth))

    def _normalize_obj(self, obj: Tag): #-> Tag:
        obj.find('h2', {'class': TITLE_CLASS_NAME}).decompose() # Remove the "Update Information" thing"

        self._apply_identation(obj)

        # we don't care about the lenght for now
        for spoiler in obj.find_all('div', {'class': SPOILER_CLASS_NAME}):
            if spoiler.text:
                spoiler.string = spoiler.text.replace("\n\nSpoiler", "")

        for block in obj.find_all("pre"):
            if block.string:
                block.string = BLOCK_START_CHAR + block.string.replace("\t", " " * TAB_SIZE) + BLOCK_START_CHAR

        # TODO: Debug
        for embed in obj.find_all('iframe', {'class': EMBED_CLASS_NAME}):
            embed_link = embed.get("src")
            if not embed.string or not embed_link:
                continue

            embed_soup = BeautifulSoup(requests.get(embed_link).text, features='html.parser')
            hyperlink = embed_soup.find('div', {'class': 'ipsRichEmbed_header ipsAreaBackground_light ipsClearfix'}).find('a', {'class': 'ipsRichEmbed_openItem'}).get("href")
            embed.string = f" {hyperlink}"

        for emoji in obj.find_all("img"):
            title = emoji.get("title")
            if title is not None:
                emoji.replace_with(title)

        for hyperlink in obj.find_all('a'):
            url = hyperlink.get('href')

            if hyperlink.string and url:
                hyperlink.string.replace_with(f" [{hyperlink.string}]({url})")

        for line_breaker in obj.find_all('br'):
            line_breaker.replace_with("\n")

    def _ddf(self, string: str) -> str:
        result = string
        for char in FORMAT_CHARS:
            result = result.replace(char, "\\" + char)

        return result

    def _apply_markdown(self, obj: Tag): #-> Tag:
        for tag in obj.find_all(DISCORD_MARKDOWN_HTML.keys()):
            template = DISCORD_MARKDOWN_HTML.get(tag.name)
            if tag.text is None or template is None:
                continue

            string = ""
            for line in tag.text.splitlines(True):
                if line.strip():
                    string += template.format(line.strip())
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
            stripped = line.strip() + ("\n" in line and "\n" or "")
            if not stripped:
                continue # Skip blank lines

            if stripped == "\n":
                # Skip the leading new lines since they will be stripped anyway.
                if newline is False and result and last_ident == 0:
                    newline = True
                    result.append("\n")

                continue

            identation_level = self._get_identation_level(line)
            prefix = self._get_identation_prefix(identation_level)
            last_line = result and result[last_text_index] or None

            # Some devs use the start for list items...
            if stripped.startswith("\\*"):
                prefix = ""

            # For patch note headers
            # Remove the aditional space between the header and first list item.
            if identation_level > 0:
                if result[len(result) - 1] == "\n" and last_ident == 0:
                    result.pop()

                # Make the header bold if it's not already.
                if last_ident == 0 and last_line and not last_line.lstrip().startswith("*"):
                    result[last_text_index] = "**" + last_line.rstrip() + "**\n"

            # For description headers
            if not stripped.startswith("**") and identation_level == 0 and last_line and last_line.lstrip().startswith("*"):
                if result[len(result) - 1] == "\n" and len(stripped) > 64 and last_line and len(last_line) < 64:
                    result.pop()

            # Make sure that the headers are one line behind descriptions.
            if identation_level == 0 and last_ident > 0 and not stripped.startswith("\n"):
                stripped = "\n" + stripped

            result.append(prefix + stripped)
            newline = False
            last_ident = identation_level
            last_text_index = len(result) - 1

        return result
