"""Extract structured article content from HTML."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

from bs4 import BeautifulSoup, NavigableString, Tag

try:
    from readability import Document  # type: ignore
except ImportError:  # pragma: no cover - fallback handled in code
    Document = None  # type: ignore


@dataclass(frozen=True)
class ContentBlock:
    type: str
    text: str | None = None
    level: int | None = None
    items: List[str] | None = None
    ordered: bool | None = None

    def to_dict(self) -> dict[str, object]:
        data: dict[str, object] = {"type": self.type}
        if self.text is not None:
            data["text"] = self.text
        if self.level is not None:
            data["level"] = self.level
        if self.items is not None:
            data["items"] = self.items
        if self.ordered is not None:
            data["ordered"] = self.ordered
        return data


def extract_content(html: str) -> List[dict[str, object]]:
    """Return structured content blocks extracted from *html*."""
    main_html = html
    if Document is not None:
        try:
            main_html = Document(html).summary(html_partial=True)
        except Exception:  # pragma: no cover - readability edge
            main_html = html

    soup = BeautifulSoup(main_html, "html.parser")
    article = soup.find("article") or soup.body or soup
    blocks: List[ContentBlock] = []

    for block in _iter_blocks(article):
        if block:
            blocks.append(block)

    return [block.to_dict() for block in blocks]


def _iter_blocks(node: Tag) -> List[ContentBlock]:
    blocks: List[ContentBlock] = []
    for child in node.children:
        if isinstance(child, NavigableString):
            continue
        if not isinstance(child, Tag):
            continue
        if child.name in {"script", "style", "noscript", "nav", "footer", "header"}:
            continue

        if child.name and child.name.startswith("h") and len(child.name) == 2 and child.name[1].isdigit():
            text = _clean(child.get_text(" ", strip=True))
            if text:
                level = int(child.name[1])
                blocks.append(ContentBlock(type="heading", text=text, level=level))
            continue

        if child.name == "p":
            text = _clean(child.get_text(" ", strip=True))
            if text:
                blocks.append(ContentBlock(type="paragraph", text=text))
            continue

        if child.name in {"ul", "ol"}:
            items = [_clean(li.get_text(" ", strip=True)) for li in child.find_all("li", recursive=False)]
            items = [item for item in items if item]
            if items:
                blocks.append(ContentBlock(type="list", items=items, ordered=child.name == "ol"))
            continue

        # Recurse into other container elements (e.g., div, section)
        blocks.extend(_iter_blocks(child))

    return blocks


def _clean(text: str) -> str:
    return " ".join(text.split())


__all__ = ["extract_content", "ContentBlock"]
