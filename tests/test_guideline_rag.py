import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from schemesetu.guidelines import ingest_pdf, load_guideline_passages
from schemesetu.models import AnalysisRequest, EligibilityStatus, UserProfile
from schemesetu.repository import SchemeRepository
from schemesetu.retrieval import HybridSchemeRetriever, LocalHashEmbeddingProvider
from schemesetu.service import SchemeSetuService


ROOT = Path(__file__).parents[1]
AICTE_ID = "myscheme-38265a91e80340be"
ASSAM_ID = "myscheme-f17ece2bc7e807e3"


class OfficialGuidelineRagTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repository = SchemeRepository.from_json(ROOT / "data/pilot_education_schemes.json")

    def _service(self, method="keyword"):
        return SchemeSetuService(
            self.repository,
            retriever=HybridSchemeRetriever(method=method, embedding_provider=LocalHashEmbeddingProvider()),
            guideline_directory=str(ROOT / "data/guidelines"),
            source_alert_path=str(ROOT / "data/source_alerts.json"),
        )

    def test_guideline_is_retrieved_with_year_and_page_but_never_verifies_scheme(self):
        with patch("schemesetu.service.date") as clock:
            clock.today.return_value.year = 2026
            clock.today.return_value.month = 9
            response = self._service().analyze(AnalysisRequest(
                query="Saksham degree disability 40 percent family income 8 lakh",
                profile=UserProfile(disability=True, family_income=500000),
                top_k=5,
                include_explanation=True,
            ))
        assessment = next(a for a in response.assessments if a.scheme_id == AICTE_ID)
        official = [e for e in assessment.evidence if e.source_type == "official_guideline"]
        self.assertTrue(official)
        self.assertTrue(all(e.academic_year == "2021-22" and e.page for e in official))
        self.assertTrue(all("aicte.gov.in" in e.source_url for e in official))
        self.assertTrue(any("2021-22" in w for w in assessment.source_warnings))
        self.assertTrue(any("2021-22" in w for w in assessment.explanation.caveats))
        self.assertEqual(assessment.eligibility_status, EligibilityStatus.POSSIBLY_ELIGIBLE)
        self.assertFalse(assessment.verified)

    def test_embedding_retrieval_keeps_official_provenance(self):
        response = self._service("embedding").analyze(AnalysisRequest(
            query="Saksham disability scholarship degree", profile=UserProfile(), top_k=5,
        ))
        assessment = next(a for a in response.assessments if a.scheme_id == AICTE_ID)
        self.assertTrue(any(e.source_type == "official_guideline" for e in assessment.evidence))

    def test_assam_discrepancy_is_labeled_as_ai_assisted(self):
        response = self._service().analyze(AnalysisRequest(
            query="Assam combined merit scholarship", profile=UserProfile(state="Assam"), top_k=10,
        ))
        assessment = next(a for a in response.assessments if a.scheme_id == ASSAM_ID)
        self.assertTrue(any("ai_assisted" in w and "male-only" in w for w in assessment.source_warnings))
        self.assertFalse(assessment.verified)

    def test_year_must_be_printed_in_pdf(self):
        # The importer rejects a claimed year rather than silently making old evidence current.
        with tempfile.TemporaryDirectory() as directory:
            pdf = Path(directory) / "guideline.pdf"
            pdf.write_bytes(b"test-pdf")
            with patch("pypdf.PdfReader") as reader:
                reader.return_value.pages = [type("Page", (), {"extract_text": lambda self: "Scheme for 2021-22"})()]
                with self.assertRaisesRegex(ValueError, "does not appear"):
                    ingest_pdf(pdf, AICTE_ID, "https://www.aicte.gov.in/example.pdf", "2026-27")

    def test_catalog_dataset_and_official_source_are_distinct(self):
        passages = load_guideline_passages(ROOT / "data/guidelines", self.repository.all())
        self.assertTrue(passages)
        self.assertTrue(all(p.source_type == "official_guideline" for p in passages))
        self.assertTrue(all(p.academic_year == "2021-22" for p in passages))
        service = self._service()
        dataset_passages = [p for p in service.retriever._passages if p.scheme_id == AICTE_ID and p.source_type == "dataset"]
        self.assertTrue(all("kaggle.com" in p.source_url for p in dataset_passages))


if __name__ == "__main__":
    unittest.main()
