import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
from urllib.error import HTTPError

from schemesetu.models import Scheme
from schemesetu.verification import ReviewDecision, list_completed_reviews, load_review
from schemesetu.verify_sources import _best_supporting_source, _split_clauses, draft_review, fetch_url, extract_text


class VerifySourcesTest(unittest.TestCase):
    def test_automation_never_emits_confirmed(self):
        scheme = Scheme(
            scheme_id="demo",
            name="Demo Scholarship",
            description="Demo",
            level="state",
            benefits="Aid",
            eligibility_text="Applicant must be a resident of Maharashtra. Family income must be below the notified limit.",
            official_source_url="https://www.myscheme.gov.in/schemes/demo",
            verified=False,
        )
        sources = [
            {
                "url": "https://example.gov.in/guideline.pdf",
                "final_url": "https://example.gov.in/guideline.pdf",
                "status": 200,
                "extracted_chars": 200,
                "text": "Applicant must be a resident of Maharashtra. Family income must be below the notified limit.",
            }
        ]
        review = draft_review(scheme, sources, reviewer="test", review_date="2026-09-28")
        self.assertTrue(review.assisted)
        self.assertFalse(review.human_confirmed)
        self.assertNotEqual(review.overall_decision, ReviewDecision.CONFIRMED)
        self.assertTrue(all(c.decision != ReviewDecision.CONFIRMED for c in review.clause_reviews))
        self.assertEqual(review.overall_decision, ReviewDecision.AMENDED)

    def test_missing_sources_are_insufficient(self):
        scheme = Scheme(
            scheme_id="demo",
            name="Demo Scholarship",
            description="Demo",
            level="state",
            benefits="Aid",
            eligibility_text="Applicant must be a resident of Maharashtra.",
            official_source_url="https://www.myscheme.gov.in/schemes/demo",
        )
        sources = [
            {
                "url": "https://www.myscheme.gov.in/schemes/demo",
                "status": 403,
                "extracted_chars": 0,
                "text": "",
                "error": "403",
            }
        ]
        review = draft_review(scheme, sources, reviewer="test", review_date="2026-09-28")
        self.assertEqual(review.overall_decision, ReviewDecision.INSUFFICIENT)
        self.assertIn("unavailable", review.notes)

    def test_myscheme_request_is_attempted_and_real_403_recorded(self):
        url = "https://www.myscheme.gov.in/schemes/demo"
        with tempfile.TemporaryDirectory() as directory:
            with patch("schemesetu.verify_sources.urlopen", side_effect=HTTPError(url, 403, "Forbidden", {}, None)) as mocked:
                meta, data = fetch_url(url, Path(directory))
                self.assertEqual(meta["status"], 403)
                self.assertEqual(data, b"")
                self.assertNotIn("Skipped automated fetch", meta["error"])
                mocked.assert_called_once()

            # A legacy synthetic 403 cache entry must not suppress a retry.
            from schemesetu.verify_sources import _cache_paths
            meta_path, _ = _cache_paths(Path(directory), url)
            meta_path.write_text(json.dumps({**meta, "error": "Skipped automated fetch: old shortcut"}))
            with patch("schemesetu.verify_sources.urlopen", side_effect=HTTPError(url, 404, "Not Found", {}, None)) as mocked:
                fresh, _ = fetch_url(url, Path(directory))
                self.assertEqual(fresh["status"], 404)
                mocked.assert_called_once()

    def test_myscheme_page_shell_is_not_scheme_evidence(self):
        meta = {"url": "https://www.myscheme.gov.in/schemes/demo", "status": 200,
                "content_type": "text/html"}
        body = b"<html><body><h1>myScheme</h1><footer>Get in touch</footer></body></html>"
        self.assertEqual(extract_text(meta, body), "")
        self.assertIn("page shell", meta["error"])

    def test_human_confirmed_filter(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            assisted = {
                "scheme_id": "a",
                "scheme_name": "A",
                "reviewer": "bot",
                "review_date": "2026-09-28",
                "overall_decision": "amended",
                "assisted": True,
                "human_confirmed": False,
                "clause_reviews": [],
            }
            (root / "a.json").write_text(json.dumps(assisted))
            self.assertEqual(list_completed_reviews(root), [])
            assisted["human_confirmed"] = True
            (root / "a.json").write_text(json.dumps(assisted))
            self.assertEqual(len(list_completed_reviews(root)), 1)

    def test_clause_split_and_support(self):
        clauses = _split_clauses("First long enough eligibility clause here. Second long enough clause appears next.")
        self.assertGreaterEqual(len(clauses), 2)
        support = _best_supporting_source(
            clauses[0],
            [{"url": "https://example.gov.in/x", "text": clauses[0], "extracted_chars": 100}],
        )
        self.assertIsNotNone(support)
        self.assertGreaterEqual(support["match_score"], 0.85)


class AssistedReviewsPresentTest(unittest.TestCase):
    def test_pilot_assisted_reviews_exist_without_confirmation(self):
        root = Path(__file__).parents[1] / "data" / "verification" / "reviews" / "assisted"
        if not root.exists():
            self.skipTest("assisted reviews not generated in this environment")
        files = list(root.glob("myscheme-*.json"))
        self.assertGreaterEqual(len(files), 25)
        for path in files[:5]:
            review = load_review(path)
            self.assertTrue(review.assisted)
            self.assertFalse(review.human_confirmed)
            self.assertNotEqual(review.overall_decision, ReviewDecision.CONFIRMED)


if __name__ == "__main__":
    unittest.main()
