from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Operator(str, Enum):
    EQUALS = "equals"
    IN = "in"
    LTE = "lte"
    GTE = "gte"
    CONTAINS = "contains"


class Rule(BaseModel):
    field: str
    operator: Operator
    value: Any
    description: str
    source_text: str | None = None
    source_url: str | None = None


class Scheme(BaseModel):
    scheme_id: str
    name: str
    description: str
    level: str
    states: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    benefits: str
    eligibility_rules: list[Rule] = Field(default_factory=list)
    required_documents: list[str] = Field(default_factory=list)
    application_url: str | None = None
    official_source_url: str | None = None
    dataset_source_url: str | None = None
    eligibility_text: str = ""
    detailed_description: str = ""
    documents_text: str = ""
    exclusions_text: str = ""
    references_text: str = ""
    application_process_text: str = ""
    scheme_close_date: str = ""
    verified: bool = False


class UserProfile(BaseModel):
    age: int | None = None
    gender: str | None = None
    state: str | None = None
    category: str | None = None
    education_level: str | None = None
    course: str | None = None
    family_income: float | None = None
    disability: bool | None = None
    available_documents: list[str] = Field(default_factory=list)


class RuleStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    UNKNOWN = "unknown"


class RuleResult(BaseModel):
    rule: Rule
    status: RuleStatus
    actual_value: Any = None
    explanation: str


class EligibilityStatus(str, Enum):
    ELIGIBLE = "eligible"
    INELIGIBLE = "ineligible"
    POSSIBLY_ELIGIBLE = "possibly_eligible"


class SchemeAssessment(BaseModel):
    scheme_id: str
    scheme_name: str
    retrieval_score: float
    eligibility_status: EligibilityStatus
    rule_results: list[RuleResult]
    missing_information: list[str]
    clarification_questions: list[str]
    missing_documents: list[str]
    readiness_score: float | None
    source_url: str | None = None
    verified: bool = False
    eligibility_text: str = ""
    documents_text: str = ""


class AnalysisRequest(BaseModel):
    query: str
    profile: UserProfile
    top_k: int = Field(default=5, ge=1, le=20)


class AnalysisResponse(BaseModel):
    query: str
    assessments: list[SchemeAssessment]
