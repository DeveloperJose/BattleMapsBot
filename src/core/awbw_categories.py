from html.parser import HTMLParser
from urllib.parse import parse_qs, urlsplit


class _CategoryParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.categories: list[str] = []
        self.found = False
        self._depth = 0
        self._label: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "div":
            if attributes.get("id") == "map-categories":
                self.found = True
                self._depth = 1
            elif self._depth:
                self._depth += 1
        if self._depth and tag == "a":
            link = urlsplit(attributes.get("href") or "")
            if link.path.lstrip(
                "/"
            ) == "categories.php" and "categories_id" in parse_qs(link.query):
                self._label = []

    def handle_data(self, data: str) -> None:
        if self._label is not None:
            self._label.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._label is not None:
            label = " ".join("".join(self._label).split())
            if label and label not in self.categories:
                self.categories.append(label)
            self._label = None
        if tag == "div" and self._depth:
            self._depth -= 1


def parse_map_categories(page: str) -> list[str]:
    """Read only the map's category links, excluding navigation and comments."""
    parser = _CategoryParser()
    parser.feed(page)
    parser.close()
    if not parser.found:
        raise ValueError("AWBW map page has no categories section")
    return parser.categories
