import urllib


class Author:

    name: str
    icon_url: str
    url: str

    def __init__(self, data):
        self.name = data['name']
        self.icon_url = urllib.parse.urlparse(data['image'], scheme='https').geturl()  # type: ignore
        self.url = urllib.parse.urlparse(data['url'], scheme='https').geturl()  # type: ignore

    def to_embed(self) -> dict[str, str]:
        return {
            "name": self.name,
            "icon_url": self.icon_url,
            "url": self.url,
        }
