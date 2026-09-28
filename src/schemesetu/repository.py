from __future__ import annotations

import json
from pathlib import Path

from .models import Scheme


class SchemeRepository:
    def __init__(self, schemes: list[Scheme]):
        self._schemes = schemes

    @classmethod
    def from_json(cls, path: str | Path) -> "SchemeRepository":
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls([Scheme.model_validate(item) for item in raw])

    def all(self) -> list[Scheme]:
        return list(self._schemes)

    def get(self, scheme_id: str) -> Scheme | None:
        return next((s for s in self._schemes if s.scheme_id == scheme_id), None)
