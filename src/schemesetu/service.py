from __future__ import annotations

from .eligibility import EligibilityEngine
from .models import AnalysisRequest, AnalysisResponse, SchemeAssessment
from .repository import SchemeRepository
from .retrieval import KeywordRetriever


class SchemeSetuService:
    def __init__(
        self,
        repository: SchemeRepository,
        retriever: KeywordRetriever | None = None,
        eligibility_engine: EligibilityEngine | None = None,
    ):
        self.repository = repository
        self.retriever = retriever or KeywordRetriever()
        self.eligibility_engine = eligibility_engine or EligibilityEngine()

    def analyze(self, request: AnalysisRequest) -> AnalysisResponse:
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
            assessments.append(
                SchemeAssessment(
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
                )
            )

        return AnalysisResponse(query=request.query, assessments=assessments)
