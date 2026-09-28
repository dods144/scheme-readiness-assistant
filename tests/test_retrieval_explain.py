import unittest

from schemesetu.explain import ExplanationService
from schemesetu.models import (
    EligibilityStatus,
    Operator,
    RetrievedEvidence,
    Rule,
    RuleStatus,
    Scheme,
    SchemeAssessment,
    UserProfile,
)
from schemesetu.passages import build_passages
from schemesetu.retrieval import (
    EmbeddingPassageRetriever,
    KeywordPassageRetriever,
    LocalHashEmbeddingProvider,
    compare_retrieval_methods,
)


def _scheme(**overrides) -> Scheme:
    base = dict(
        scheme_id="demo-scholarship",
        name="Demo State Scholarship",
        description="Scholarship support for undergraduate engineering students.",
        level="state",
        states=["Maharashtra"],
        categories=["Education & Learning"],
        benefits="Tuition assistance",
        eligibility_text="Applicant must be a resident of Maharashtra with family income below the notified limit.",
        exclusions_text="Students already receiving another central scholarship are excluded.",
        documents_text="Aadhaar card and income certificate are required.",
        references_text="https://www.myscheme.gov.in/schemes/demo",
        official_source_url="https://www.myscheme.gov.in/schemes/demo",
        verified=False,
    )
    base.update(overrides)
    return Scheme(**base)


class RetrievalAttributionTest(unittest.TestCase):
    def test_passages_keep_scheme_section_and_source(self):
        passages = build_passages([_scheme()])
        sections = {passage.section for passage in passages}
        self.assertIn("eligibility", sections)
        self.assertIn("exclusions", sections)
        self.assertIn("documents", sections)
        self.assertIn("references", sections)
        for passage in passages:
            self.assertEqual(passage.scheme_id, "demo-scholarship")
            self.assertEqual(passage.source_url, "https://www.myscheme.gov.in/schemes/demo")
            self.assertTrue(passage.text)

    def test_keyword_and_embedding_return_attributed_evidence(self):
        passages = build_passages([_scheme()])
        query = "Maharashtra undergraduate scholarship income certificate"
        keyword_hits = KeywordPassageRetriever().search(query, passages, top_k=5)
        embedding_hits = EmbeddingPassageRetriever(LocalHashEmbeddingProvider()).search(
            query, passages, top_k=5
        )
        self.assertGreater(len(keyword_hits), 0)
        self.assertGreater(len(embedding_hits), 0)
        for hit in keyword_hits + embedding_hits:
            self.assertEqual(hit.scheme_id, "demo-scholarship")
            self.assertTrue(hit.section)
            self.assertTrue(hit.source_url)
            self.assertTrue(hit.retrieval_method)

    def test_compare_retrieval_methods_reports_overlap_without_scores(self):
        result = compare_retrieval_methods(
            "engineering scholarship Maharashtra",
            [_scheme()],
            top_k=3,
            embedding_provider=LocalHashEmbeddingProvider(),
        )
        self.assertIn("keyword_scheme_ids", result)
        self.assertIn("embedding_scheme_ids", result)
        self.assertIn("overlap_scheme_ids", result)
        self.assertNotIn("precision", result)
        self.assertNotIn("recall", result)
        self.assertIn("not evaluation scores", result["note"])


class EvidenceAndExplanationGuardTest(unittest.TestCase):
    def setUp(self):
        self.explainer = ExplanationService(api_key="")

    def _assessment(self, evidence: list[RetrievedEvidence], status=EligibilityStatus.POSSIBLY_ELIGIBLE):
        return SchemeAssessment(
            scheme_id="demo-scholarship",
            scheme_name="Demo State Scholarship",
            retrieval_score=0.5,
            eligibility_status=status,
            rule_results=[],
            missing_information=[],
            clarification_questions=[],
            missing_documents=[],
            readiness_score=None,
            verified=False,
            evidence=evidence,
        )

    def test_missing_evidence_is_explicit(self):
        explanation = self.explainer.explain(self._assessment([]), evidence=[], use_llm=False)
        self.assertEqual(explanation.confidence, "insufficient")
        self.assertIn("Insufficient information", explanation.summary)
        self.assertIn("not verified", explanation.summary.casefold())

    def test_conflicting_passages_add_caveat(self):
        evidence = [
            RetrievedEvidence(
                scheme_id="demo-scholarship",
                scheme_name="Demo State Scholarship",
                section="eligibility",
                text="Residents of Maharashtra may apply.",
                source_url="https://www.myscheme.gov.in/schemes/demo",
                score=0.9,
                retrieval_method="keyword",
            ),
            RetrievedEvidence(
                scheme_id="demo-scholarship",
                scheme_name="Demo State Scholarship",
                section="exclusions",
                text="Students receiving another scholarship are excluded.",
                source_url="https://www.myscheme.gov.in/schemes/demo",
                score=0.8,
                retrieval_method="keyword",
            ),
        ]
        explanation = self.explainer.explain(self._assessment(evidence), evidence=evidence)
        self.assertTrue(any("exclusion" in caveat.casefold() for caveat in explanation.caveats))
        self.assertTrue(explanation.citations)
        self.assertIn("not verified", explanation.summary.casefold())

    def test_llm_guard_blocks_unverified_eligible_claim(self):
        from schemesetu.explain import _guard_unverified_claim

        summary, confidence, caveats = _guard_unverified_claim(
            "You are eligible for this scheme based on the dataset text.",
            "high",
            [],
            verified=False,
            has_evidence=True,
        )
        self.assertTrue(summary.startswith("Not verified:"))
        self.assertEqual(confidence, "insufficient")
        self.assertTrue(any("unverified eligibility" in item.casefold() for item in caveats))


class FalseEligibilityPreventionTest(unittest.TestCase):
    def test_dataset_prose_without_rules_is_not_eligible(self):
        from schemesetu.eligibility import EligibilityEngine

        scheme = _scheme(eligibility_rules=[])
        status, _, _, _ = EligibilityEngine().evaluate(
            scheme,
            UserProfile(state="Maharashtra", family_income=100000),
        )
        self.assertEqual(status, EligibilityStatus.POSSIBLY_ELIGIBLE)

    def test_passing_unverified_rules_are_not_eligible(self):
        from schemesetu.eligibility import EligibilityEngine

        scheme = _scheme(
            eligibility_rules=[
                Rule(
                    field="state",
                    operator=Operator.EQUALS,
                    value="Maharashtra",
                    description="Must reside in Maharashtra",
                )
            ]
        )
        status, results, _, _ = EligibilityEngine().evaluate(
            scheme, UserProfile(state="Maharashtra")
        )
        self.assertEqual(results[0].status, RuleStatus.PASSED)
        self.assertEqual(status, EligibilityStatus.POSSIBLY_ELIGIBLE)


if __name__ == "__main__":
    unittest.main()
