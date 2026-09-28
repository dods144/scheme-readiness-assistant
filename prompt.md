I’m continuing my SchemeSetu capstone project in this repository. First inspect the README, models, importer, retrieval, eligibility engine, service, API, tests, and data files before changing code.

Project goal: Help users discover Indian education and scholarship schemes, check application readiness, and explain results using retrieved source evidence. The final capstone should compare retrieval approaches and report measured results from a real, independently reviewed evaluation set.

Current state:
- The repo has a working FastAPI MVP, keyword retrieval, deterministic eligibility rules, and tests.
- `data/pilot_education_schemes.json` contains 25 real but unverified records for a fresh clone.
- The public Kaggle “MyScheme India: 4670 Govt Welfare Schemes” dataset has 4,670 rows. Its `schemes.csv` is available locally at `data/raw/schemes.csv`; add `data/raw/` to `.gitignore` before using it.
- `python -m schemesetu.import_myscheme data/raw/schemes.csv` produces 1,104 education and scholarship records under `data/imported/`. The API uses that full catalog when it exists, otherwise the pilot.
- Imported eligibility and document fields are source text, not verified executable rules. Imported records must remain `verified: false` and must not produce a definite “eligible” claim.
- `data/import_report.json` records the input hash and mapping. A separate `schemes_faqs.csv` exists in the dataset but is not in this repo yet.
- All 7 existing tests passed at the last handoff.

Please work in small, reviewable stages:

1. Run the importer against the local CSV, inspect data quality, and confirm the counts and source links. Fix any genuine mapping or filtering problems you find.
2. Implement the first RAG retrieval stage using scheme descriptions, eligibility text, exclusions, document text, and references. Keep each retrieved passage tied to its scheme ID, source URL, and section. Compare keyword retrieval with an embedding-based approach; make the embedding provider configurable.
3. Add an optional LLM explanation step using `OPENAI_API_KEY` from the environment. Give the LLM retrieved passages and the deterministic rule results. Require source citations and an explicit “not verified” or “insufficient information” response when evidence is weak. Never let the LLM silently create eligibility rules or claim eligibility from dataset prose alone.
4. Prepare a workflow for manually verifying an initial 25–40 schemes against current myScheme pages and linked government guidelines. Store the exact clause, URL, review date, and reviewer decision for each rule. Do not invent verification outcomes or evaluation examples.
5. Add meaningful tests for source attribution, missing evidence, conflicting passages, and preventing false eligibility claims. Run the tests and show actual output.

Do not fabricate evaluation data, scores, citations, or experiment results. Do not commit the raw CSV, generated full catalog, `.env`, or API key. Explain what you changed, what remains unverified, and the next reviewable milestone.