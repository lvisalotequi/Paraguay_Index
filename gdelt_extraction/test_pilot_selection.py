import unittest
from prepare_pilot_selection import prepare, number


class SelectionTests(unittest.TestCase):
    def test_retained_decisions_and_fields(self):
        result = prepare()
        self.assertEqual(result["counts"], {"include": 9})
        self.assertEqual(result["selection"], "include_only")
        self.assertEqual(len(result["articles"]), 9)
        self.assertEqual({r["review_id"] for r in result["articles"]}, {2, 3, 7, 8, 10, 14, 19, 28, 29})
        for row in result["articles"]:
            self.assertNotIn("persons", row)
            self.assertNotIn("themes", row)
            self.assertEqual(row["eligible_for_confirmed_metrics"], row["decision"] == "include")
            self.assertEqual(row["decision"], "include")
            self.assertTrue(row["eligible_for_confirmed_metrics"])
            self.assertEqual(row["unresolved"], [])
            self.assertEqual(set(row["tone"]), {"tone", "positive_score", "negative_score", "polarity"})

    def test_missing_is_not_zero(self):
        self.assertIsNone(number(""))
        self.assertEqual(number("0"), 0)
        with self.assertRaises(ValueError):
            number("NaN")


if __name__ == "__main__":
    unittest.main()
