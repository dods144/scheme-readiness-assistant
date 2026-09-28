# Manual scheme verification workflow

This directory holds clause-level verification records. Do not invent review outcomes,
evaluation examples, or scores.

## Goal

Independently verify an initial **25–40** education/scholarship schemes against the current
[myScheme](https://www.myscheme.gov.in/) page and linked government guidelines before treating
any rule as executable ground truth.

## Observed access constraint (2026-09-28)

Automated fetches of `www.myscheme.gov.in/schemes/...` currently receive **HTTP 403**.
Assisted reviews therefore rely on linked guideline URLs from `references_text` when those
URLs respond. Humans should still open the myScheme page in a normal browser during dual-check.

## Process

1. Run the assist tool against the pilot catalog:

```bash
PYTHONPATH=src python -m schemesetu.verify_sources \
  --catalog data/pilot_education_schemes.json \
  --reviewer "your-name-or-assist-id"
```

2. Inspect drafts in `reviews/assisted/`. Automation may emit only `amended` or `insufficient`
   (never `confirmed`, never `verified=true` on catalog records).
3. Open `catalog_source_url` and each clause `official_url` in a browser.
4. For each clause, copy the **exact official clause**, URL, and review date; set decision to
   `confirmed`, `amended`, `rejected`, or `insufficient`.
5. Save the human-final JSON under `reviews/{scheme_id}.json` with:
   - `assisted: false` (or keep provenance in notes)
   - `human_confirmed: true`
6. Only then consider promoting confirmed clauses into executable `eligibility_rules` and
   flipping catalog `verified` after dual review.

## File layout

- `review_template.json` — blank shape for manual entry
- `reviews/assisted/` — machine-assisted drafts (`human_confirmed: false`)
- `reviews/*.json` — human-confirmed reviews only
- `fetch_report.json` — HTTP status / extraction summary from the last assist run
- `cache/` — local HTTP cache (gitignored)

## What not to do

- Do not fabricate clauses, URLs, review dates, or decisions.
- Do not treat assisted drafts as an evaluation set.
- Do not mark imported prose verified solely because overlap scores looked high.
