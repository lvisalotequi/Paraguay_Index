"""Offline integrity and failure-mode tests for the pilot's curated records."""

import unittest

from validate_pilot_review import read_json, validate


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.review = read_json("classification_v1.json")
        self.catalogue = read_json("media_catalogue_v1.json")
        self.original = read_json("pilot_review.json")

    def check(self):
        return validate(self.review, self.catalogue, self.original)

    def test_complete_review(self):
        result = self.check()
        self.assertEqual(result["decisions"], {"include": 9, "exclude": 41, "doubtful": 17})
        self.assertEqual(result["domains"], 31)

    def test_duplicate_url_rejected(self):
        self.review["articles"][0]["url"] = self.review["articles"][1]["url"]
        with self.assertRaises(ValueError):
            self.check()

    def test_missing_domain_rejected(self):
        self.catalogue["sources"].pop()
        with self.assertRaises(ValueError):
            self.check()

    def test_unavailable_inclusion_rejected(self):
        self.review["articles"][1]["content_access"] = "unavailable"
        with self.assertRaises(ValueError):
            self.check()

    def test_false_verified_country_rejected(self):
        source = next(s for s in self.catalogue["sources"] if s["verification_status"] == "unverified")
        source["country_verified"] = "US"
        with self.assertRaises(ValueError):
            self.check()

    def test_incorrect_totals_rejected(self):
        self.review["counts"]["include"] += 1
        with self.assertRaises(ValueError):
            self.check()


if __name__ == "__main__":
    unittest.main()
