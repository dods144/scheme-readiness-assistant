"""Local official-document passage store, with explicit source and year provenance."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from pydantic import BaseModel, Field

from .models import Scheme, SourcePassage


class GuidelineChunk(BaseModel):
    page: int = Field(ge=1)
    text: str = Field(min_length=1)


class GuidelineDocument(BaseModel):
    scheme_id: str
    source_url: str
    academic_year: str  # Supplied by the reviewer from the PDF, never inferred as current.
    sha256: str
    chunks: list[GuidelineChunk]


class SourceAlert(BaseModel):
    scheme_id: str
    message: str
    source_url: str
    review_status: str = "ai_assisted"


def load_source_alerts(path: str | Path, schemes: list[Scheme]) -> dict[str, list[SourceAlert]]:
    source = Path(path)
    if not source.exists():
        return {}
    valid_ids = {scheme.scheme_id for scheme in schemes}
    alerts: dict[str, list[SourceAlert]] = {}
    for item in json.loads(source.read_text(encoding="utf-8")):
        alert = SourceAlert.model_validate(item)
        if alert.scheme_id in valid_ids:
            alerts.setdefault(alert.scheme_id, []).append(alert)
    return alerts


def _chunk_page(text: str, limit: int = 900) -> list[str]:
    """Keep bounded, readable passages without crossing a PDF page boundary."""
    paragraphs = [re.sub(r"\s+", " ", part).strip() for part in re.split(r"\n\s*\n", text)]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if not paragraph:
            continue
        # Some PDFs have no paragraph breaks; split their text at sentence boundaries.
        parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", paragraph)
        for part in parts:
            if current and len(current) + len(part) + 1 > limit:
                chunks.append(current)
                current = ""
            if len(part) > limit:
                if current:
                    chunks.append(current)
                    current = ""
                chunks.extend(part[i:i + limit] for i in range(0, len(part), limit))
            else:
                current = f"{current} {part}".strip()
    if current:
        chunks.append(current)
    return chunks


def ingest_pdf(pdf: Path, scheme_id: str, source_url: str, academic_year: str) -> GuidelineDocument:
    """Extract a local PDF. The supplied year must match a year printed in the PDF."""
    from pypdf import PdfReader

    if not re.fullmatch(r"\d{4}-\d{2}", academic_year):
        raise ValueError("academic_year must look like 2021-22")
    raw = pdf.read_bytes()
    pages = [(page.extract_text() or "") for page in PdfReader(pdf).pages]
    if academic_year not in " ".join(pages):
        raise ValueError(f"Academic year {academic_year} does not appear in the PDF")
    chunks = [
        GuidelineChunk(page=page_number, text=chunk)
        for page_number, page_text in enumerate(pages, 1)
        for chunk in _chunk_page(page_text)
        if len(chunk) >= 40
    ]
    if not chunks:
        raise ValueError("No extractable guideline passages found")
    return GuidelineDocument(
        scheme_id=scheme_id,
        source_url=source_url,
        academic_year=academic_year,
        sha256=hashlib.sha256(raw).hexdigest(),
        chunks=chunks,
    )


def load_guideline_passages(directory: str | Path, schemes: list[Scheme]) -> list[SourcePassage]:
    """Load curated documents only for schemes in this catalog."""
    root = Path(directory)
    names = {scheme.scheme_id: scheme.name for scheme in schemes}
    passages: list[SourcePassage] = []
    if not root.exists():
        return passages
    for path in sorted(root.glob("*.json")):
        doc = GuidelineDocument.model_validate_json(path.read_text(encoding="utf-8"))
        if doc.scheme_id not in names:
            continue
        for chunk in doc.chunks:
            passages.append(SourcePassage(
                scheme_id=doc.scheme_id,
                scheme_name=names[doc.scheme_id],
                section="official_guideline",
                text=chunk.text,
                source_url=doc.source_url,
                source_type="official_guideline",
                academic_year=doc.academic_year,
                page=chunk.page,
            ))
    return passages


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract attributable passages from an official PDF")
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--scheme-id", required=True)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--academic-year", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    document = ingest_pdf(args.pdf, args.scheme_id, args.source_url, args.academic_year)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(document.model_dump_json(indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(document.chunks)} passages to {args.output}")


if __name__ == "__main__":
    main()
