"""Optional LLM explanations grounded in retrieved passages and rule results."""

from __future__ import annotations

import json
import os
import re
from typing import Any
from urllib import error, request

from .models import (
    EligibilityStatus,
    Explanation,
    RetrievedEvidence,
    RuleResult,
    SchemeAssessment,
)


SYSTEM_PROMPT = """You help applicants understand Indian education or scholarship schemes.
You receive deterministic rule results and retrieved source passages.
Rules:
- Cite only the provided passages by scheme_id and section.
- Never invent eligibility rules.
- Never claim a scheme is eligible from dataset prose alone.
- If the scheme is unverified, or evidence is weak/missing/conflicting, say so explicitly
  using "not verified" or "insufficient information".
- Prefer "possibly eligible" wording when verification is incomplete.
- Keep the summary under 120 words.
Return JSON with keys: summary (string), confidence (one of high|medium|low|insufficient),
caveats (array of strings).
"""


def _conflict_caveats(evidence: list[RetrievedEvidence]) -> list[str]:
    by_section: dict[str, list[RetrievedEvidence]] = {}
    for item in evidence:
        by_section.setdefault(item.section, []).append(item)
    caveats: list[str] = []
    eligibility = by_section.get("eligibility", [])
    exclusions = by_section.get("exclusions", [])
    if eligibility and exclusions:
        caveats.append(
            "Eligibility and exclusion passages both matched; review both before applying."
        )
    return caveats


def _template_explanation(
    assessment: SchemeAssessment,
    evidence: list[RetrievedEvidence],
) -> Explanation:
    caveats = [*_conflict_caveats(evidence), *assessment.source_warnings]
    if not evidence:
        return Explanation(
            summary=(
                f"Insufficient information: no source passages were retrieved for "
                f"{assessment.scheme_name}. Eligibility remains not verified."
            ),
            confidence="insufficient",
            citations=[],
            caveats=["missing evidence"],
            provider="template",
        )

    if not assessment.verified:
        caveats.append("Scheme rules/source text are not verified against current official guidance.")

    if assessment.eligibility_status == EligibilityStatus.INELIGIBLE:
        summary = (
            f"Deterministic checks indicate {assessment.scheme_name} is currently ineligible "
            f"for the supplied profile. Review the cited passages; the catalog remains "
            f"{'verified' if assessment.verified else 'not verified'}."
        )
        confidence = "medium" if assessment.verified else "low"
    elif assessment.eligibility_status == EligibilityStatus.ELIGIBLE:
        summary = (
            f"Verified deterministic rules currently pass for {assessment.scheme_name}. "
            f"Confirm the cited official clauses before applying."
        )
        confidence = "high"
    else:
        summary = (
            f"Possibly relevant: {assessment.scheme_name}. Status is possibly eligible / "
            f"not verified from the available passages. Do not treat dataset prose as a "
            f"definite eligibility decision."
        )
        confidence = "low" if evidence else "insufficient"

    return Explanation(
        summary=summary,
        confidence=confidence,
        citations=evidence[:5],
        caveats=caveats,
        provider="template",
    )


def _rule_payload(results: list[RuleResult]) -> list[dict[str, Any]]:
    return [
        {
            "field": result.rule.field,
            "status": result.status.value,
            "description": result.rule.description,
            "explanation": result.explanation,
            "source_url": result.rule.source_url,
        }
        for result in results
    ]


def _guard_unverified_claim(
    summary: str,
    confidence: str,
    caveats: list[str],
    *,
    verified: bool,
    has_evidence: bool,
) -> tuple[str, str, list[str]]:
    updated_caveats = list(caveats)
    if not verified and re.search(r"\beligible\b", summary, re.I):
        if not re.search(r"not verified|insufficient|possibly", summary, re.I):
            summary = (
                f"Not verified: {summary.rstrip('.')} "
                f"Dataset or provisional rules alone cannot establish eligibility."
            )
            confidence = "insufficient"
            updated_caveats.append(
                "Model wording adjusted to avoid an unverified eligibility claim."
            )
    if not has_evidence:
        confidence = "insufficient"
        updated_caveats.append("missing evidence")
    return summary, confidence, list(dict.fromkeys(updated_caveats))


class ExplanationService:
    """Builds grounded explanations; uses OpenAI only when explicitly requested and keyed."""

    def __init__(self, api_key: str | None = None, model: str = "gpt-4o-mini"):
        self.api_key = api_key if api_key is not None else os.environ.get("OPENAI_API_KEY", "")
        self.model = model

    def explain(
        self,
        assessment: SchemeAssessment,
        evidence: list[RetrievedEvidence] | None = None,
        use_llm: bool = False,
    ) -> Explanation:
        passages = evidence if evidence is not None else assessment.evidence
        baseline = _template_explanation(assessment, passages)
        if not use_llm:
            return baseline
        if not self.api_key:
            baseline.caveats = [
                *baseline.caveats,
                "OPENAI_API_KEY not set; returned template explanation.",
            ]
            return baseline
        try:
            return self._llm_explain(assessment, passages, baseline)
        except (error.URLError, TimeoutError, KeyError, json.JSONDecodeError, ValueError) as exc:
            baseline.caveats = [*baseline.caveats, f"LLM explanation unavailable: {exc}"]
            return baseline

    def _llm_explain(
        self,
        assessment: SchemeAssessment,
        evidence: list[RetrievedEvidence],
        baseline: Explanation,
    ) -> Explanation:
        if not evidence and assessment.eligibility_status != EligibilityStatus.INELIGIBLE:
            return baseline

        user_payload = {
            "scheme_id": assessment.scheme_id,
            "scheme_name": assessment.scheme_name,
            "verified": assessment.verified,
            "eligibility_status": assessment.eligibility_status.value,
            "rule_results": _rule_payload(assessment.rule_results),
            "passages": [
                {
                    "scheme_id": item.scheme_id,
                    "section": item.section,
                    "source_url": item.source_url,
                    "source_type": item.source_type,
                    "academic_year": item.academic_year,
                    "page": item.page,
                    "text": item.text[:1200],
                }
                for item in evidence[:6]
            ],
            "instructions": (
                "If verified is false, you must not claim the applicant is eligible. "
                "If passages are empty or conflicting, say insufficient information or not verified. "
                "Treat dated guideline passages as historical unless verified for the current cycle."
            ),
            "source_warnings": assessment.source_warnings,
        }
        body = {
            "model": self.model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(user_payload)},
            ],
        }
        req = request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with request.urlopen(req, timeout=60) as response:
            payload = json.loads(response.read().decode("utf-8"))
        content = payload["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        summary = str(parsed.get("summary") or "").strip()
        confidence = str(parsed.get("confidence") or "insufficient").casefold()
        caveats = [str(item) for item in parsed.get("caveats") or []]
        summary, confidence, caveats = _guard_unverified_claim(
            summary,
            confidence,
            [*baseline.caveats, *caveats],
            verified=assessment.verified,
            has_evidence=bool(evidence),
        )
        return Explanation(
            summary=summary or baseline.summary,
            confidence=confidence if confidence in {"high", "medium", "low", "insufficient"} else "insufficient",
            citations=evidence[:5],
            caveats=caveats,
            provider="openai",
        )
