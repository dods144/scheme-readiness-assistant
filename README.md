# SchemeSetu MVP

SchemeSetu evaluates whether a user appears eligible for selected education and scholarship schemes and whether the application has enough information and documents to proceed.

The first implementation deliberately separates three responsibilities:

1. Retrieval finds potentially relevant schemes.
2. A deterministic rule engine checks measurable eligibility conditions.
3. A clarification layer asks for information that is still required.

Public datasets are treated as retrieval sources, not as unquestioned ground truth. Detailed rules should be verified against official scheme documents before being added to the evaluation set.

## Current features

- Canonical Pydantic models for schemes and user profiles
- JSON repository with a small illustrative dataset
- Keyword and metadata retrieval baseline
- Deterministic eligibility evaluation
- Missing-information questions
- Required-document readiness calculation
- FastAPI endpoint for analysis
- Unit tests for boundary conditions and end-to-end analysis

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn schemesetu.api:app --reload
```

Example request:

```bash
curl -X POST http://127.0.0.1:8000/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "query": "scholarship for a female engineering student in Maharashtra",
    "profile": {
      "age": 21,
      "gender": "female",
      "state": "Maharashtra",
      "education_level": "undergraduate",
      "course": "engineering",
      "family_income": 350000,
      "available_documents": ["aadhaar_card", "marksheet"]
    }
  }'
```

## Run tests without installing FastAPI

The core tests use the Python standard library and Pydantic already available in the environment:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

## Import the public myScheme dataset

The default API catalog contains 25 real, unverified scholarship records from [MyScheme India: 4670 Govt Welfare Schemes](https://www.kaggle.com/datasets/elchemist/myscheme-india-govt-welfare-schemes), one per state/UT where possible. It is a pilot for browsing, not an evaluation set. The publisher lists the dataset under CC0 and describes 4,670 schemes and a separate `schemes_faqs.csv`. The original CSV is not committed to this repository. The FAQ file is reserved for the next RAG milestone.

To use the full education catalog, download `schemes.csv` and run:

```bash
PYTHONPATH=src python -m schemesetu.import_myscheme /path/to/schemes.csv --inspect
PYTHONPATH=src python -m schemesetu.import_myscheme /path/to/schemes.csv
SCHEMESETU_CATALOG=data/imported/education_schemes.json uvicorn schemesetu.api:app --reload
```

The importer reports rows read, education schemes imported, mapped columns, and government source links. If the publisher uses different headers, pass `--map mapping.json`, for example `{"name": "Scheme Title", "category": "Sector", "eligibility": "Who Can Apply", "url": "Scheme Link"}`. The API automatically uses the full imported catalog when it exists; otherwise it uses the 25-record pilot. The filter includes the dataset's `Education & Learning` category plus schemes explicitly named as scholarships, education loans, or student stipends. Eligibility and document text is retained for discovery, but no numerical rules or document checklist is inferred automatically; imported records have `verified: false` and cannot be marked eligible solely because the dataset mentioned them. Review each scheme against the linked government page before adding rule objects and an evaluation case.

The supplied CSV produced **1,104** records from 4,670 source rows. See `data/import_report.json` for the column mapping and SHA-256 of that input. The pilot is derived from the same file; it contains unverified source material and must not be used as an evaluation set. A locally generated full catalog stays under `data/imported/`, which is excluded from Git.

## Next implementation steps

- Inspect the downloaded dataset schema and validate the adapter mapping against it
- Normalize state, category, document and eligibility fields
- Add embedding retrieval and reranking
- Store source passages and clause-level citations
- Create the independently reviewed evaluation set
- Add source-conflict detection across dataset and official documents
