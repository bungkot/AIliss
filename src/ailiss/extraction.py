from html.parser import HTMLParser
from urllib.parse import urlparse


class TextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._skip = 0
        self.text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "template"}:
            self._skip += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "template"} and self._skip:
            self._skip -= 1

    def handle_data(self, data: str) -> None:
        if not self._skip:
            value = " ".join(data.split())
            if value:
                self.text.append(value)


def parse_fixture_html(html: str) -> list[str]:
    parser = TextParser()
    parser.feed(html)
    return parser.text


def canonicalize_domain(value: str) -> str | None:
    value = value.strip().lower()
    parsed = urlparse(value if "://" in value else f"https://{value}")
    hostname = parsed.hostname
    if not hostname or parsed.scheme != "https":
        return None
    hostname = hostname.rstrip(".")
    if hostname.startswith("www."):
        hostname = hostname[4:]
    return hostname


def normalize_company_name(value: str) -> str:
    normalized = " ".join(value.strip().lower().split())
    normalized = normalized.replace(".", "")
    normalized = normalized.replace(",", "")
    for prefix in ("pt ", "cv "):
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix) :].strip()
    if normalized.endswith(" indonesia"):
        normalized = normalized[: -len(" indonesia")].rstrip()
    for suffix in (" pt", " cv"):
        if normalized.endswith(suffix):
            normalized = normalized[: -len(suffix)].rstrip()
    return normalized


def normalize_email(value: str) -> str | None:
    normalized = value.strip().lower()
    if normalized.count("@") != 1:
        return None
    local, domain = normalized.rsplit("@", 1)
    domain = canonicalize_domain(domain)
    return f"{local}@{domain}" if domain else None
