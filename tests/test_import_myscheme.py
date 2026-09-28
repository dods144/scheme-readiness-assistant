import csv
import tempfile
import unittest
from pathlib import Path

from schemesetu.import_myscheme import import_csv
from schemesetu.models import AnalysisRequest, EligibilityStatus, UserProfile
from schemesetu.repository import SchemeRepository
from schemesetu.service import SchemeSetuService


class MySchemeImportTest(unittest.TestCase):
    def test_import_keeps_prose_unverified_and_avoids_eligibility_claim(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "schemes.csv"
            with source.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=[
                    "slug", "scheme_name", "categories", "brief_description", "eligibility", "documents_required",
                    "source_url", "state", "exclusions", "references",
                ])
                writer.writeheader()
                writer.writerow({
                    "slug": "student", "scheme_name": "Student Scholarship", "categories": "Education & Learning",
                    "brief_description": "Support for students", "eligibility": "Income below a threshold",
                    "documents_required": "Income certificate", "source_url": "https://www.myscheme.gov.in/schemes/student",
                    "state": "Maharashtra", "exclusions": "Already receiving aid", "references": "Guideline link",
                })
                writer.writerow({"scheme_name": "Housing Support", "categories": "Housing",
                                 "brief_description": "Helps families with students"})
                writer.writerow({"slug": "student", "scheme_name": "Student Scholarship", "categories": "Education & Learning",
                                 "source_url": "https://www.myscheme.gov.in/schemes/student"})

            schemes, report = import_csv(source)
            self.assertEqual(report["input_rows"], 3)
            self.assertEqual(report["imported_schemes"], 1)
            scheme = schemes[0]
            self.assertFalse(scheme.verified)
            self.assertEqual(scheme.eligibility_rules, [])
            self.assertEqual(scheme.eligibility_text, "Income below a threshold")
            self.assertEqual(scheme.documents_text, "Income certificate")
            self.assertEqual(scheme.exclusions_text, "Already receiving aid")
            self.assertEqual(scheme.required_documents, [])
            response = SchemeSetuService(SchemeRepository(schemes)).analyze(
                AnalysisRequest(query="scholarship student", profile=UserProfile(state="Maharashtra"))
            )
            self.assertEqual(response.assessments[0].eligibility_status,
                             EligibilityStatus.POSSIBLY_ELIGIBLE)
            self.assertIsNone(response.assessments[0].readiness_score)
            self.assertFalse(response.assessments[0].verified)
            self.assertEqual(response.assessments[0].eligibility_text, "Income below a threshold")

    def test_non_government_url_is_not_presented_as_official(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "schemes.csv"
            source.write_text("title,details,link\nScholarship,Education help,https://example.com/scheme\n")
            schemes, _ = import_csv(source)
            self.assertIsNone(schemes[0].official_source_url)


if __name__ == "__main__":
    unittest.main()
