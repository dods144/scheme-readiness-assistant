import unittest

from schemesetu.eligibility import EligibilityEngine
from schemesetu.models import EligibilityStatus, Operator, Rule, Scheme, UserProfile


def scheme_with(rule: Rule) -> Scheme:
    return Scheme(
        scheme_id="test",
        name="Test Scheme",
        description="Test",
        level="state",
        benefits="Test",
        eligibility_rules=[rule],
        required_documents=["income_certificate", "marksheet"],
    )


class EligibilityEngineTest(unittest.TestCase):
    def setUp(self):
        self.engine = EligibilityEngine()

    def test_income_boundary_passes(self):
        scheme = scheme_with(
            Rule(
                field="family_income",
                operator=Operator.LTE,
                value=400000,
                description="Income must not exceed INR 400,000.",
            )
        )
        scheme.verified = True
        status, results, _, _ = self.engine.evaluate(
            scheme, UserProfile(family_income=400000)
        )
        self.assertEqual(status, EligibilityStatus.ELIGIBLE)
        self.assertEqual(results[0].status.value, "passed")

    def test_unverified_scheme_cannot_be_marked_eligible(self):
        scheme = scheme_with(
            Rule(
                field="family_income",
                operator=Operator.LTE,
                value=400000,
                description="Income must not exceed INR 400,000.",
            )
        )
        self.assertFalse(scheme.verified)
        status, _, _, _ = self.engine.evaluate(
            scheme, UserProfile(family_income=400000)
        )
        self.assertEqual(status, EligibilityStatus.POSSIBLY_ELIGIBLE)

    def test_missing_value_requests_clarification(self):
        scheme = scheme_with(
            Rule(
                field="family_income",
                operator=Operator.LTE,
                value=400000,
                description="Income must not exceed INR 400,000.",
            )
        )
        status, _, missing, questions = self.engine.evaluate(scheme, UserProfile())
        self.assertEqual(status, EligibilityStatus.POSSIBLY_ELIGIBLE)
        self.assertEqual(missing, ["family_income"])
        self.assertIn("annual family income", questions[0])

    def test_failed_rule_makes_scheme_ineligible(self):
        scheme = scheme_with(
            Rule(
                field="age",
                operator=Operator.LTE,
                value=25,
                description="Age must not exceed 25.",
            )
        )
        status, _, _, _ = self.engine.evaluate(scheme, UserProfile(age=26))
        self.assertEqual(status, EligibilityStatus.INELIGIBLE)

    def test_document_readiness(self):
        scheme = scheme_with(
            Rule(field="age", operator=Operator.LTE, value=25, description="Age limit")
        )
        missing, score = self.engine.document_readiness(
            scheme, UserProfile(available_documents=["marksheet"])
        )
        self.assertEqual(missing, ["income_certificate"])
        self.assertEqual(score, 50.0)


if __name__ == "__main__":
    unittest.main()
