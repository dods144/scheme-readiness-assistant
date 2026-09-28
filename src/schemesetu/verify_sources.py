"""Assist human verification by fetching linked sources and drafting review shells.

Does not invent confirmation outcomes. Decisions are set to `insufficient` unless
extracted official text appears to support a catalog clause (then `amended`).
myScheme pages that return HTTP errors or only the site shell are recorded
as inaccessible rather than fabricated.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from datetime import date
from html.parser import HTMLParser
from io import BytesIO
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from urllib.parse import urlparse

from .models import Scheme
from .repository import SchemeRepository
from .verification import ReviewDecision, SchemeVerificationReview, ClauseReview

UA = "Mozilla/5.0 (compatible; SchemeSetuVerification/0.1; educational research)"
URL_RE = re.compile(r"https?://[^\s|\"<>]+", re.I)


class _HTMLText(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.skip = False

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[override]
        if tag in {"script", "style", "noscript"}:
            self.skip = True

    def handle_endtag(self, tag: str) -> None:  # type: ignore[override]
        if tag in {"script", "style", "noscript"}:
            self.skip = False

    def handle_data(self, data: str) -> None:  # type: ignore[override]
        if not self.skip:
            text = data.strip()
            if text:
                self.parts.append(text)


def _clean_url(url: str) -> str:
    return url.strip().rstrip(".;,)")


def _normalize(text: str) -> str:
    text = re.sub(r"&#\d+;|&amp;|&nbsp;|&lt;|&gt;|&quot;", " ", text)
    return re.sub(r"\s+", " ", text).strip().casefold()


def _split_clauses(text: str) -> list[str]:
    parts = re.split(r"[;\n]+|(?<=\.)\s+(?=[A-Z])", text)
    return [part.strip(" .;") for part in parts if len(part.strip(" .;")) >= 20]


def _cache_paths(cache_dir: Path, url: str) -> tuple[Path, Path]:
    key = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
    return cache_dir / f"{key}.meta.json", cache_dir / f"{key}.bin"


MAX_DOWNLOAD_BYTES = 4_000_000


def _is_myscheme(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return host == "myscheme.gov.in" or host.endswith(".myscheme.gov.in")


def fetch_url(url: str, cache_dir: Path, force: bool = False) -> tuple[dict, bytes]:
    url = _clean_url(url)
    meta_path, body_path = _cache_paths(cache_dir, url)
    if not force and meta_path.exists() and body_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        # Older versions stored a synthetic 403 without making a request.
        # Refresh that entry so the report reflects a real HTTP response.
        if not (meta.get("error") or "").startswith("Skipped automated fetch:"):
            data = body_path.read_bytes()
            if len(data) > MAX_DOWNLOAD_BYTES:
                meta = {
                    **meta,
                    "skipped_large": True,
                    "error": meta.get("error")
                    or f"Cached body {len(data)} exceeds {MAX_DOWNLOAD_BYTES} bytes; skipped extraction",
                    "bytes": len(data),
                }
                return meta, b""
            return meta, data

    req = Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    data = b""
    meta: dict
    try:
        with urlopen(req, timeout=20) as response:
            length = response.headers.get("Content-Length")
            if length and int(length) > MAX_DOWNLOAD_BYTES:
                meta = {
                    "url": url,
                    "final_url": response.geturl(),
                    "status": 200,
                    "content_type": response.headers.get("Content-Type", ""),
                    "error": f"Skipped download: Content-Length {length} exceeds {MAX_DOWNLOAD_BYTES} bytes",
                    "bytes": 0,
                    "skipped_large": True,
                }
            else:
                chunks: list[bytes] = []
                total = 0
                skipped_large = False
                while True:
                    chunk = response.read(64_000)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > MAX_DOWNLOAD_BYTES:
                        skipped_large = True
                        chunks = []
                        break
                    chunks.append(chunk)
                if skipped_large:
                    meta = {
                        "url": url,
                        "final_url": response.geturl(),
                        "status": 200,
                        "content_type": response.headers.get("Content-Type", ""),
                        "error": f"Truncated download after {MAX_DOWNLOAD_BYTES} bytes",
                        "bytes": total,
                        "skipped_large": True,
                    }
                else:
                    data = b"".join(chunks)
                    meta = {
                        "url": url,
                        "final_url": response.geturl(),
                        "status": getattr(response, "status", 200),
                        "content_type": response.headers.get("Content-Type", ""),
                        "error": None,
                        "bytes": len(data),
                    }
    except HTTPError as exc:
        meta = {
            "url": url,
            "final_url": url,
            "status": exc.code,
            "content_type": exc.headers.get("Content-Type", "") if exc.headers else "",
            "error": str(exc),
            "bytes": 0,
        }
    except (URLError, TimeoutError, OSError) as exc:
        meta = {
            "url": url,
            "final_url": url,
            "status": None,
            "content_type": "",
            "error": repr(exc),
            "bytes": 0,
        }

    cache_dir.mkdir(parents=True, exist_ok=True)
    body_path.write_bytes(data)
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return meta, data


def extract_text(meta: dict, data: bytes) -> str:
    if not data or meta.get("status") != 200 or meta.get("skipped_large"):
        return ""
    content_type = (meta.get("content_type") or "").lower()
    final_url = (meta.get("final_url") or meta.get("url") or "").lower()
    if "pdf" in content_type or final_url.endswith(".pdf") or data[:4] == b"%PDF":
        try:
            from pypdf import PdfReader
        except ImportError as exc:  # pragma: no cover - optional dependency path
            raise SystemExit("pypdf is required to extract PDF guidelines; pip install pypdf") from exc
        try:
            reader = PdfReader(BytesIO(data), strict=False)
            return "\n".join((page.extract_text() or "") for page in reader.pages[:12])
        except Exception as exc:
            meta["extract_error"] = repr(exc)
            return ""
    if (
        "html" in content_type
        or final_url.endswith((".html", ".htm", ".aspx", ".jsp", ".php"))
        or b"<html" in data[:800].lower()
    ):
        parser = _HTMLText()
        parser.feed(data.decode("utf-8", errors="replace"))
        text = "\n".join(parser.parts)
        if _is_myscheme(meta.get("final_url") or meta.get("url") or ""):
            # A 200 response can be the JavaScript app shell, whose footer
            # has no scheme clauses. It cannot support an assisted review.
            if not re.search(r"\b(eligibility|documents required|application process)\b", text, re.I):
                meta["error"] = "myScheme returned a page shell without scheme details"
                return ""
        return text
    try:
        return data.decode("utf-8", errors="replace")
    except Exception:
        return ""


def collect_urls(scheme: Scheme) -> list[str]:
    urls: list[str] = []
    if scheme.official_source_url:
        urls.append(scheme.official_source_url)
    urls.extend(URL_RE.findall(scheme.references_text or ""))
    cleaned = []
    seen = set()
    for url in urls:
        url = _clean_url(url)
        if url and url not in seen:
            seen.add(url)
            cleaned.append(url)
    return cleaned


def _best_supporting_source(clause: str, sources: list[dict]) -> dict | None:
    needle = _normalize(clause)
    if len(needle) < 20:
        return None
    # Prefer longer exact/near substrings from government guideline docs over myScheme.
    tokens = [t for t in re.findall(r"[a-z0-9]{4,}", needle)]
    best = None
    best_score = 0.0
    for source in sources:
        text = _normalize(source.get("text") or "")
        if not text:
            continue
        if needle in text:
            score = 1.0
        else:
            hits = sum(1 for token in tokens if token in text)
            score = hits / max(len(tokens), 1)
        if score > best_score:
            best_score = score
            best = {**source, "match_score": round(score, 3)}
    if best and best_score >= 0.55:
        return best
    return None


def draft_review(
    scheme: Scheme,
    sources: list[dict],
    reviewer: str,
    review_date: str,
) -> SchemeVerificationReview:
    usable = [s for s in sources if (s.get("extracted_chars") or 0) > 80]
    myscheme_blocked = any(
        _is_myscheme(s.get("url") or "") and
        (s.get("status") != 200 or not s.get("text"))
        for s in sources
    )

    clause_reviews: list[ClauseReview] = []
    for clause in _split_clauses(scheme.eligibility_text)[:8]:
        support = _best_supporting_source(clause, usable)
        if support and support.get("match_score", 0) >= 0.55:
            # Automation never emits `confirmed`; a human must dual-check before that decision.
            decision = ReviewDecision.AMENDED
            excerpt = (support.get("text") or "")[:400].strip()
            official_clause = excerpt or clause
            rationale = (
                f"Automated textual overlap with {support['url']} "
                f"(match_score={support['match_score']}). "
                f"Pending human dual-check before any `confirmed` decision or rule promotion."
            )
            official_url = support.get("final_url") or support["url"]
        else:
            decision = ReviewDecision.INSUFFICIENT
            official_clause = ""
            official_url = scheme.official_source_url or (sources[0]["url"] if sources else "")
            rationale = (
                "No sufficiently matching official text was extracted from available sources."
            )
            if myscheme_blocked:
                rationale += " myScheme page was inaccessible during automated fetch."
        clause_reviews.append(
            ClauseReview(
                field_target="eligibility_unstructured",
                dataset_passage=clause,
                official_clause=official_clause,
                official_url=official_url or "",
                section="eligibility",
                review_date=review_date,
                decision=decision,
                reviewer=reviewer,
                rationale=rationale,
            )
        )

    if not clause_reviews:
        clause_reviews.append(
            ClauseReview(
                field_target="eligibility_unstructured",
                dataset_passage=scheme.eligibility_text or "(empty)",
                official_clause="",
                official_url=scheme.official_source_url or "",
                section="eligibility",
                review_date=review_date,
                decision=ReviewDecision.INSUFFICIENT,
                reviewer=reviewer,
                rationale="No eligibility clauses available in the catalog record.",
            )
        )

    decisions = {item.decision for item in clause_reviews}
    if ReviewDecision.AMENDED in decisions:
        overall = ReviewDecision.AMENDED
    else:
        overall = ReviewDecision.INSUFFICIENT

    notes = []
    if myscheme_blocked:
        notes.append("myScheme scheme details were unavailable; guideline links were used when available.")
    if not usable:
        notes.append("No usable extracted text from linked sources at review time.")
    notes.append(
        "Automated assist draft only. No clause is marked confirmed. "
        "A human must dual-check before promoting executable rules or setting verified=true."
    )

    return SchemeVerificationReview(
        scheme_id=scheme.scheme_id,
        scheme_name=scheme.name,
        catalog_source_url=scheme.official_source_url,
        reviewer=reviewer,
        review_date=review_date,
        overall_decision=overall,
        notes=" ".join(notes),
        assisted=True,
        human_confirmed=False,
        clause_reviews=clause_reviews,
    )


def run_batch(
    catalog: Path,
    output_dir: Path,
    cache_dir: Path,
    reviewer: str,
    limit: int | None = None,
    force: bool = False,
) -> dict:
    repo = SchemeRepository.from_json(catalog)
    schemes = repo.all()[: limit or None]
    output_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)
    review_date = date.today().isoformat()
    fetch_report = []
    written = []

    for scheme in schemes:
        sources = []
        for url in collect_urls(scheme):
            meta, data = fetch_url(url, cache_dir, force=force)
            text = extract_text(meta, data)
            sources.append({**meta, "extracted_chars": len(text), "text": text})
            time.sleep(0.25)
        review = draft_review(scheme, sources, reviewer=reviewer, review_date=review_date)
        path = output_dir / f"{scheme.scheme_id}.json"
        path.write_text(
            json.dumps(review.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        written.append(str(path))
        fetch_report.append(
            {
                "scheme_id": scheme.scheme_id,
                "name": scheme.name,
                "review_path": str(path),
                "overall_decision": review.overall_decision.value,
                "fetches": [
                    {
                        "url": s["url"],
                        "status": s.get("status"),
                        "extracted_chars": s.get("extracted_chars"),
                        "error": s.get("error"),
                    }
                    for s in sources
                ],
            }
        )

    report_path = output_dir.parent.parent / "fetch_report.json"
    if output_dir.name != "assisted":
        report_path = output_dir.parent / "fetch_report.json"
    report_path.write_text(json.dumps(fetch_report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    summary = {
        "schemes": len(schemes),
        "reviews_written": len(written),
        "review_date": review_date,
        "overall_counts": {
            decision.value: sum(1 for item in fetch_report if item["overall_decision"] == decision.value)
            for decision in ReviewDecision
        },
        "fetch_report": str(report_path),
    }
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--catalog",
        type=Path,
        default=Path("data/pilot_education_schemes.json"),
        help="Scheme catalog JSON to review",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/verification/reviews/assisted"),
        help="Directory for assisted review JSON files (not human-confirmed)",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path("data/verification/cache"),
        help="HTTP response cache (gitignored)",
    )
    parser.add_argument("--reviewer", default="schemesetu-automation+human-pending")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--force-fetch", action="store_true")
    args = parser.parse_args()
    summary = run_batch(
        catalog=args.catalog,
        output_dir=args.output_dir,
        cache_dir=args.cache_dir,
        reviewer=args.reviewer,
        limit=args.limit,
        force=args.force_fetch,
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
