"""Models and helpers for manual clause-level scheme verification.

No review outcomes are invented. Callers supply human decisions only.
"""

from __future__ import annotations

import json
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field


class ReviewDecision(str, Enum):
    CONFIRMED = "confirmed"
    AMENDED = "amended"
    REJECTED = "rejected"
    INSUFFICIENT = "insufficient"


class ClauseReview(BaseModel):
    field_target: str
    dataset_passage: str
    official_clause: str
    official_url: str
    section: str
    review_date: str
    decision: ReviewDecision
    reviewer: str
    rationale: str = ""


class SchemeVerificationReview(BaseModel):
    scheme_id: str
    scheme_name: str
    catalog_source_url: str | None = None
    reviewer: str
    review_date: str
    overall_decision: ReviewDecision
    notes: str = ""
    assisted: bool = False
    human_confirmed: bool = False
    clause_reviews: list[ClauseReview] = Field(default_factory=list)

    def has_invented_placeholders(self) -> bool:
        blob = json.dumps(self.model_dump(mode="json"))
        return "REPLACE_WITH" in blob or "YYYY-MM-DD" in blob


def load_review(path: str | Path) -> SchemeVerificationReview:
    return SchemeVerificationReview.model_validate(
        json.loads(Path(path).read_text(encoding="utf-8"))
    )


def list_completed_reviews(
    directory: str | Path,
    *,
    require_human_confirmed: bool = True,
) -> list[SchemeVerificationReview]:
    """Load reviews. By default only human-confirmed reviews count as complete."""
    root = Path(directory)
    if not root.exists():
        return []
    reviews: list[SchemeVerificationReview] = []
    for path in sorted(root.glob("*.json")):
        if path.name in {"review_template.json", "fetch_report.json"}:
            continue
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict) or "scheme_id" not in raw:
            continue
        review = SchemeVerificationReview.model_validate(raw)
        if review.has_invented_placeholders():
            raise ValueError(f"{path} still contains template placeholders")
        if require_human_confirmed:
            if review.human_confirmed:
                reviews.append(review)
        else:
            reviews.append(review)
    return reviews
