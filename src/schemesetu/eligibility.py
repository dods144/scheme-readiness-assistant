from __future__ import annotations

from typing import Any

from .models import (
    EligibilityStatus,
    Operator,
    Rule,
    RuleResult,
    RuleStatus,
    Scheme,
    UserProfile,
)


QUESTION_TEMPLATES = {
    "age": "What is your age?",
    "gender": "What gender is specified for the application?",
    "state": "Which state or union territory are you a resident of?",
    "category": "Which social category applies to you, if any?",
    "education_level": "What is your current education level?",
    "course": "Which course are you currently studying?",
    "family_income": "What is your annual family income?",
    "disability": "Do you have a disability certificate applicable to this scheme?",
}


def _normalize(value: Any) -> Any:
    if isinstance(value, str):
        return value.strip().casefold()
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    return value


class EligibilityEngine:
    def evaluate_rule(self, rule: Rule, profile: UserProfile) -> RuleResult:
        actual = getattr(profile, rule.field, None)
        if actual is None:
            return RuleResult(
                rule=rule,
                status=RuleStatus.UNKNOWN,
                actual_value=None,
                explanation=f"{rule.field} is required to evaluate this condition.",
            )

        expected = rule.value
        normalized_actual = _normalize(actual)
        normalized_expected = _normalize(expected)

        try:
            passed = self._compare(rule.operator, normalized_actual, normalized_expected)
        except (TypeError, ValueError):
            return RuleResult(
                rule=rule,
                status=RuleStatus.UNKNOWN,
                actual_value=actual,
                explanation="The provided value could not be compared with this rule.",
            )

        return RuleResult(
            rule=rule,
            status=RuleStatus.PASSED if passed else RuleStatus.FAILED,
            actual_value=actual,
            explanation=(
                f"Passed: {rule.description}"
                if passed
                else f"Failed: {rule.description}"
            ),
        )

    @staticmethod
    def _compare(operator: Operator, actual: Any, expected: Any) -> bool:
        if operator == Operator.EQUALS:
            return actual == expected
        if operator == Operator.IN:
            return actual in expected
        if operator == Operator.LTE:
            return float(actual) <= float(expected)
        if operator == Operator.GTE:
            return float(actual) >= float(expected)
        if operator == Operator.CONTAINS:
            return expected in actual
        raise ValueError(f"Unsupported operator: {operator}")

    def evaluate(self, scheme: Scheme, profile: UserProfile) -> tuple[
        EligibilityStatus, list[RuleResult], list[str], list[str]
    ]:
        results = [self.evaluate_rule(rule, profile) for rule in scheme.eligibility_rules]
        failed = [result for result in results if result.status == RuleStatus.FAILED]
        unknown = [result for result in results if result.status == RuleStatus.UNKNOWN]

        if failed:
            status = EligibilityStatus.INELIGIBLE
        elif unknown:
            status = EligibilityStatus.POSSIBLY_ELIGIBLE
        else:
            status = EligibilityStatus.ELIGIBLE

        missing_fields = list(dict.fromkeys(result.rule.field for result in unknown))
        questions = [
            QUESTION_TEMPLATES.get(field, f"Please provide {field.replace('_', ' ')}.")
            for field in missing_fields
        ]
        return status, results, missing_fields, questions

    @staticmethod
    def document_readiness(scheme: Scheme, profile: UserProfile) -> tuple[list[str], float]:
        available = {document.casefold() for document in profile.available_documents}
        missing = [doc for doc in scheme.required_documents if doc.casefold() not in available]
        if not scheme.required_documents:
            return [], 100.0
        ready_count = len(scheme.required_documents) - len(missing)
        return missing, round(100 * ready_count / len(scheme.required_documents), 1)
