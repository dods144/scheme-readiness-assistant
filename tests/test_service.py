import unittest
from pathlib import Path

from schemesetu.models import AnalysisRequest, EligibilityStatus, UserProfile
from schemesetu.repository import SchemeRepository
from schemesetu.service import SchemeSetuService


class SchemeSetuServiceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        data_path = Path(__file__).parents[1] / "data" / "sample_schemes.json"
        cls.service = SchemeSetuService(SchemeRepository.from_json(data_path))

    def test_end_to_end_analysis(self):
        request = AnalysisRequest(
            query="scholarship for female engineering student in Maharashtra",
            profile=UserProfile(
                age=21,
                gender="female",
                state="Maharashtra",
                education_level="undergraduate",
                course="engineering",
                family_income=350000,
                available_documents=["aadhaar_card", "marksheet"],
            ),
            top_k=3,
        )
        response = self.service.analyze(request)
        self.assertGreater(len(response.assessments), 0)
        first = response.assessments[0]
        self.assertEqual(first.scheme_id, "maha-girls-engineering-demo")
        self.assertEqual(first.eligibility_status, EligibilityStatus.POSSIBLY_ELIGIBLE)
        self.assertFalse(first.verified)
        self.assertIn("income_certificate", first.missing_documents)


if __name__ == "__main__":
    unittest.main()
