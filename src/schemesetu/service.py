from __future__ import annotations

import os
from datetime import date

from .eligibility import EligibilityEngine
from .explain import ExplanationService
from .models import AnalysisRequest, AnalysisResponse, SchemeAssessment
from .guidelines import load_guideline_passages, load_source_alerts
from .repository import SchemeRepository
from .retrieval import HybridSchemeRetriever, KeywordRetriever, compare_retrieval_methods


class SchemeSetuService:
    def __init__(
        self,
        repository: SchemeRepository,
        retriever: HybridSchemeRetriever | KeywordRetriever | None = None,
        eligibility_engine: EligibilityEngine | None = None,
        explanation_service: ExplanationService | None = None,
        guideline_directory: str | None = None,
        source_alert_path: str | None = None,
    ):
        self.repository = repository
        self.retriever = retriever or HybridSchemeRetriever()
        self.eligibility_engine = eligibility_engine or EligibilityEngine()
        self.explanation_service = explanation_service or ExplanationService()
        self.guideline_passages = load_guideline_passages(guideline_directory, self.repository.all()) if guideline_directory else []
        self.source_alerts = load_source_alerts(source_alert_path, self.repository.all()) if source_alert_path else {}
        if hasattr(self.retriever, "prepare"):
            self.retriever.prepare(self.repository.all(), self.guideline_passages)

    def analyze(self, request: AnalysisRequest) -> AnalysisResponse:
        method = request.retrieval_method or getattr(self.retriever, "method", None) or os.environ.get(
            "SCHEMESETU_RETRIEVAL", "keyword"
        )
        if isinstance(self.retriever, HybridSchemeRetriever) and request.retrieval_method:
            self.retriever.method = request.retrieval_method.casefold()
            if self.retriever.method.startswith("embedding"):
                self.retriever.prepare(self.repository.all(), self.guideline_passages)

        retrieved = self.retriever.search(
            query=request.query,
            profile=request.profile,
            schemes=self.repository.all(),
            top_k=request.top_k,
        )

        assessments: list[SchemeAssessment] = []
        for item in retrieved:
            scheme = item.scheme
            status, rule_results, missing_fields, questions = self.eligibility_engine.evaluate(
                scheme, request.profile
            )
            missing_documents, readiness_score = self.eligibility_engine.document_readiness(
                scheme, request.profile
            )
            evidence = list(getattr(item, "evidence", ()) or ())
            current_year = date.today().year - (date.today().month < 6)
            warnings = sorted({
                f"Retrieved guideline is for {hit.academic_year}; current-year eligibility clauses are unconfirmed."
                for hit in evidence
                if hit.source_type == "official_guideline" and hit.academic_year
                and int(hit.academic_year[:4]) != current_year
            })
            warnings.extend(
                f"{alert.review_status} source discrepancy: {alert.message} Source: {alert.source_url}"
                for alert in self.source_alerts.get(scheme.scheme_id, [])
            )
            assessment = SchemeAssessment(
                scheme_id=scheme.scheme_id,
                scheme_name=scheme.name,
                retrieval_score=item.score,
                eligibility_status=status,
                rule_results=rule_results,
                missing_information=missing_fields,
                clarification_questions=questions,
                missing_documents=missing_documents,
                readiness_score=(readiness_score if scheme.required_documents else None),
                source_url=scheme.official_source_url,
                verified=scheme.verified,
                eligibility_text=scheme.eligibility_text,
                documents_text=scheme.documents_text,
                evidence=evidence,
                source_warnings=warnings,
            )
            if request.include_explanation:
                assessment.explanation = self.explanation_service.explain(
                    assessment,
                    evidence=evidence,
                    use_llm=bool(os.environ.get("OPENAI_API_KEY")),
                )
            assessments.append(assessment)

        comparison = None
        if os.environ.get("SCHEMESETU_COMPARE_RETRIEVAL", "").lower() in {"1", "true", "yes"}:
            comparison = compare_retrieval_methods(
                request.query,
                self.repository.all(),
                top_k=request.top_k,
                guideline_passages=self.guideline_passages,
            )

        return AnalysisResponse(
            query=request.query,
            assessments=assessments,
            retrieval_method=method,
            comparison=comparison,
        )
