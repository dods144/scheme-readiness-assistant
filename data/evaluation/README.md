# Evaluation set (not yet populated)

This directory will hold an **independently reviewed** evaluation set used to measure
keyword vs embedding retrieval.

## Rules

- Do not invent queries, relevance labels, citations, or metric scores.
- Evaluation cases may be added only after corresponding scheme reviews in
  `data/verification/reviews/` are `human_confirmed: true` with clause-level
  `confirmed` or carefully justified `amended` decisions.
- Assisted drafts under `data/verification/reviews/assisted/` are **not** evaluation
  ground truth.

## Planned case shape

```json
{
  "case_id": "eval-001",
  "query": "human-authored information need",
  "relevant_scheme_ids": ["myscheme-..."],
  "notes": "Why these schemes are relevant, tied to reviewed clauses",
  "reviewer": "name",
  "review_date": "YYYY-MM-DD"
}
```

No cases are checked in yet because human dual-check of the pilot reviews is still pending.
