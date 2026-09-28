"""Convert the Kaggle myScheme CSV into an unverified discovery catalog.

Use --inspect first: the dataset publisher can change column names between
versions. --map accepts a JSON file mapping canonical field names to CSV headers.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlparse

from .models import Scheme


DATASET_URL = "https://www.kaggle.com/datasets/elchemist/myscheme-india-govt-welfare-schemes"
FIELDS = {
    "name": ("scheme_name", "name", "title", "scheme"),
    "slug": ("slug", "scheme_slug"),
    "description": ("brief_description", "description", "details", "scheme_description", "summary"),
    "detailed_description": ("detailed_description",),
    "category": ("category", "categories", "scheme_category", "tags"),
    "sub_categories": ("sub_categories",),
    "benefits": ("benefits", "benefit", "scheme_benefits"),
    "eligibility": ("eligibility", "eligibility_criteria", "eligibility_details"),
    "documents": ("documents_required", "documents", "required_documents"),
    "exclusions": ("exclusions",),
    "references": ("references",),
    "application_process": ("application_process",),
    "scheme_close_date": ("scheme_close_date",),
    "url": ("scheme_url", "url", "source_url", "link"),
    "application_url": ("application_url", "apply_url", "application_link"),
    "state": ("state", "states", "state_ut"),
    "level": ("level", "scheme_level", "government_level"),
}
EDUCATION_TITLE = re.compile(
    r"\b(scholarship|education(?:al)? loan|student stipend|stipend to .+ students)\b", re.I
)


def _header_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def _text(value: str | None) -> str:
    return (value or "").strip()


def _list(value: str) -> list[str]:
    return [part.strip() for part in value.split(";") if part.strip()]


def _url(value: str | None) -> str | None:
    value = _text(value)
    parsed = urlparse(value)
    return value if parsed.scheme in {"https", "http"} and parsed.netloc else None


def _government_url(value: str | None) -> str | None:
    url = _url(value)
    if not url:
        return None
    host = (urlparse(url).hostname or "").lower()
    return url if host.endswith(".gov.in") or host == "gov.in" else None


def _columns(headers: list[str], overrides: dict[str, str]) -> dict[str, str]:
    normalized = {_header_key(header): header for header in headers}
    unknown = set(overrides) - set(FIELDS)
    if unknown:
        raise ValueError(f"Unknown mapping keys: {', '.join(sorted(unknown))}")
    result = {}
    for field, candidates in FIELDS.items():
        if field in overrides:
            if overrides[field] not in headers:
                raise ValueError(f"Column {overrides[field]!r} for {field} is absent from CSV")
            result[field] = overrides[field]
        else:
            match = next((normalized[key] for key in candidates if key in normalized), None)
            if match:
                result[field] = match
    if "name" not in result:
        raise ValueError("No scheme name column found; use --map to identify it")
    if not ({"description", "category", "eligibility"} & result.keys()):
        raise ValueError("No description, category, or eligibility column found")
    return result


def import_csv(path: Path, mapping: dict[str, str] | None = None) -> tuple[list[Scheme], dict[str, object]]:
    csv.field_size_limit(10_000_000)
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError("CSV has no header row")
        columns = _columns(reader.fieldnames, mapping or {})
        schemes: list[Scheme] = []
        seen: set[str] = set()
        rows = 0
        for row in reader:
            rows += 1
            def get(field: str) -> str:
                return _text(row.get(columns[field])) if field in columns else ""

            name = get("name")
            category = get("category")
            description = get("description") or get("detailed_description")
            eligibility = get("eligibility")
            # Prefer publisher category; admit explicitly named scholarships
            # even when categorized under social welfare or another sector.
            if not name or not ("Education & Learning" in _list(category)
                                or EDUCATION_TITLE.search(name)):
                continue
            source_url = _government_url(get("url"))
            identity = get("slug") or source_url or name.casefold()
            scheme_id = "myscheme-" + hashlib.sha256(identity.encode()).hexdigest()[:16]
            if scheme_id in seen:
                continue
            seen.add(scheme_id)
            schemes.append(Scheme(
                scheme_id=scheme_id,
                name=name,
                description=description,
                level=get("level") or "unknown",
                states=[get("state")] if get("state") and get("state").casefold() != "none" else [],
                categories=_list(category) + _list(get("sub_categories")),
                benefits=get("benefits"),
                eligibility_text=eligibility,
                detailed_description=get("detailed_description"),
                documents_text=get("documents"),
                exclusions_text=get("exclusions"),
                references_text=get("references"),
                application_process_text=get("application_process"),
                scheme_close_date=get("scheme_close_date"),
                application_url=_url(get("application_url")),
                official_source_url=source_url,
                dataset_source_url=DATASET_URL,
                verified=False,
            ))
    return schemes, {"input_rows": rows, "imported_schemes": len(schemes), "columns": columns,
                     "with_government_source_url": sum(bool(s.official_source_url) for s in schemes)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Downloaded scheme CSV from the Kaggle dataset")
    parser.add_argument("--inspect", action="store_true", help="Print headers without importing")
    parser.add_argument("--map", dest="mapping", type=Path, help="JSON mapping canonical fields to actual CSV headers")
    parser.add_argument("--output", type=Path, default=Path("data/imported/education_schemes.json"))
    args = parser.parse_args()
    if args.inspect:
        with args.input.open(encoding="utf-8-sig", newline="") as handle:
            print(json.dumps(csv.DictReader(handle).fieldnames, indent=2))
        return
    mapping = json.loads(args.mapping.read_text(encoding="utf-8")) if args.mapping else {}
    schemes, report = import_csv(args.input, mapping)
    if not schemes:
        raise SystemExit("No education schemes matched; inspect CSV and column mapping")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps([s.model_dump(mode="json") for s in schemes],
                                      ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({**report, "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
