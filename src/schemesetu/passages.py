"""Build source passages from scheme records for RAG retrieval."""

from __future__ import annotations

from .models import Scheme, SourcePassage

PASSAGE_SECTIONS: tuple[tuple[str, str], ...] = (
    ("description", "description"),
    ("detailed_description", "detailed_description"),
    ("eligibility", "eligibility_text"),
    ("exclusions", "exclusions_text"),
    ("documents", "documents_text"),
    ("references", "references_text"),
    ("benefits", "benefits"),
)


def build_passages(schemes: list[Scheme]) -> list[SourcePassage]:
    """Split scheme prose into attributable passages."""
    passages: list[SourcePassage] = []
    for scheme in schemes:
        source_url = scheme.official_source_url or scheme.dataset_source_url
        for section, attr in PASSAGE_SECTIONS:
            text = (getattr(scheme, attr) or "").strip()
            if not text:
                continue
            passages.append(
                SourcePassage(
                    scheme_id=scheme.scheme_id,
                    scheme_name=scheme.name,
                    section=section,
                    text=text,
                    source_url=source_url,
                )
            )
    return passages
