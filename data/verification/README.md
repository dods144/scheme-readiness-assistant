# Manual scheme verification workflow

This directory holds **human-reviewed** clause-level verification records. Do not invent
review outcomes, evaluation examples, or scores here.

## Goal

Independently verify an initial **25–40** education/scholarship schemes against the current
[myScheme](https://www.myscheme.gov.in/) page and linked government guidelines before treating
any rule as executable ground truth.

## Process

1. Pick a scheme from `data/pilot_education_schemes.json` or `data/imported/education_schemes.json`.
2. Open `official_source_url` (expected host: `www.myscheme.gov.in`) and any linked guideline URLs
   in `references_text`.
3. For each candidate eligibility or document condition, copy the **exact clause text**, the
   **URL**, and today's **review date**.
4. Record a reviewer decision using only:
   - `confirmed` — clause matches current official guidance; safe to encode as a rule later
   - `amended` — dataset prose differs; store the corrected clause from the official source
   - `rejected` — do not encode; outdated, incomplete, or non-actionable
   - `insufficient` — official page lacks enough detail
5. Save one JSON file per scheme under `reviews/` using `review_template.json` as the shape.
6. Leave `verified: false` on catalog records until a maintainer explicitly promotes confirmed
   rules into the scheme object and flips verification after dual review.

## File naming

`reviews/{scheme_id}.json`

## What not to do

- Do not fabricate clauses, URLs, review dates, or decisions.
- Do not mark imported prose as verified solely because the Kaggle row looked plausible.
- Do not use unverified reviews as an evaluation set for retrieval metrics.
