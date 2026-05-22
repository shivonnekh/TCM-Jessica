"""AcupointImageMap — match 穴位 names in text → local images.

Used by FAQ Agent: when KB returns an acupressure card, we scan the
card's text content for known point names and attach matching images
to the payload so Writer can include them in media_to_send.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger("tools.acupoint_images")

DEFAULT_INDEX_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "data" / "acupoints" / "index.json"
)


@dataclass(frozen=True)
class AcupointImage:
    zh: str          # canonical name (e.g. 天容穴)
    aliases: tuple[str, ...]
    image_path: str  # e.g. data/media/acupoints/tianrong.jpg


class AcupointImageMap:
    def __init__(self, index_path: str | Path = DEFAULT_INDEX_PATH) -> None:
        data = json.loads(Path(index_path).read_text(encoding="utf-8"))
        self._points: list[AcupointImage] = []
        for raw in data.get("points", []):
            self._points.append(
                AcupointImage(
                    zh=raw["zh"],
                    aliases=tuple(raw.get("aliases", [])),
                    image_path=raw["image"],
                )
            )
        # Build lookup: any alias OR zh → image
        self._by_term: dict[str, AcupointImage] = {}
        for p in self._points:
            self._by_term[p.zh] = p
            for a in p.aliases:
                self._by_term[a] = p

    @property
    def all_points(self) -> list[AcupointImage]:
        return list(self._points)

    def find_in_text(self, text: str, *, max_results: int = 4) -> list[AcupointImage]:
        """Return points whose Chinese name or alias appears in text."""
        if not text:
            return []
        seen: set[str] = set()
        out: list[AcupointImage] = []
        # Match longer terms first to avoid 「太衝」 also matching 「太」
        terms = sorted(self._by_term.keys(), key=len, reverse=True)
        for term in terms:
            if term in text:
                pt = self._by_term[term]
                if pt.zh in seen:
                    continue
                seen.add(pt.zh)
                out.append(pt)
                if len(out) >= max_results:
                    break
        return out

    @staticmethod
    def absolute_url(image_path: str) -> str:
        """Convert relative path 'data/media/acupoints/x.jpg' to absolute URL."""
        base = os.environ.get(
            "PUBLIC_BASE_URL", "https://tcm-jessica.onrender.com"
        ).rstrip("/")
        rel = image_path
        if rel.startswith("data/"):
            rel = rel[len("data/"):]
        if not rel.startswith("/"):
            rel = "/" + rel
        # data/media/... → /media/...
        if rel.startswith("/media/"):
            return f"{base}{rel}"
        return f"{base}/{rel.lstrip('/')}"
