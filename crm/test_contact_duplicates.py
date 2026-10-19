import unittest

from crm.contact_duplicates import detect_duplicate_emails


class DetectDuplicateEmailsTests(unittest.TestCase):
    def test_existing_conflict(self):
        rows = [
            {"line": 2, "email": "Alice@example.com", "name": "ignored"},
        ]
        existing_emails = [" alice@example.com "]

        result = detect_duplicate_emails(rows, existing_emails)

        self.assertEqual(
            result,
            [
                {
                    "line": 2,
                    "email": "alice@example.com",
                    "existing": True,
                    "previous_line": None,
                }
            ],
        )

    def test_batch_conflict_and_first_occurrence_remembered(self):
        rows = [
            {"line": 2, "email": "bob@example.com"},
            {"line": 3, "email": "BOB@example.com"},
            {"line": 4, "email": "bob@example.com"},
        ]
        existing_emails = []

        result = detect_duplicate_emails(rows, existing_emails)

        self.assertEqual(
            result,
            [
                {
                    "line": 3,
                    "email": "bob@example.com",
                    "existing": False,
                    "previous_line": 2,
                },
                {
                    "line": 4,
                    "email": "bob@example.com",
                    "existing": False,
                    "previous_line": 2,
                },
            ],
        )

    def test_first_occurrence_remembered_when_already_existing(self):
        rows = [
            {"line": 2, "email": "carol@example.com"},
            {"line": 3, "email": "carol@example.com"},
        ]
        existing_emails = ["carol@example.com"]

        result = detect_duplicate_emails(rows, existing_emails)

        self.assertEqual(
            result,
            [
                {
                    "line": 2,
                    "email": "carol@example.com",
                    "existing": True,
                    "previous_line": None,
                },
                {
                    "line": 3,
                    "email": "carol@example.com",
                    "existing": True,
                    "previous_line": 2,
                },
            ],
        )

    def test_both_reasons_on_one_row(self):
        rows = [
            {"line": 2, "email": "dave@example.com"},
            {"line": 3, "email": "dave@example.com"},
        ]
        existing_emails = ["dave@example.com"]

        result = detect_duplicate_emails(rows, existing_emails)

        self.assertEqual(
            result,
            [
                {
                    "line": 2,
                    "email": "dave@example.com",
                    "existing": True,
                    "previous_line": None,
                },
                {
                    "line": 3,
                    "email": "dave@example.com",
                    "existing": True,
                    "previous_line": 2,
                },
            ],
        )

    def test_case_and_whitespace_policy(self):
        rows = [
            {"line": 2, "email": "  Eve@example.com  "},
            {"line": 3, "email": "EVE@EXAMPLE.COM"},
        ]
        existing_emails = ["eve@example.com"]

        result = detect_duplicate_emails(rows, existing_emails)

        self.assertEqual(
            result,
            [
                {
                    "line": 2,
                    "email": "eve@example.com",
                    "existing": True,
                    "previous_line": None,
                },
                {
                    "line": 3,
                    "email": "eve@example.com",
                    "existing": True,
                    "previous_line": 2,
                },
            ],
        )

    def test_blank_emails_are_ignored(self):
        rows = [
            {"line": 2, "email": "   "},
            {"line": 3, "email": ""},
            {"line": 4, "email": "blank@example.com"},
            {"line": 5, "email": "blank@example.com"},
        ]
        existing_emails = ["", "   "]

        result = detect_duplicate_emails(rows, existing_emails)

        self.assertEqual(
            result,
            [
                {
                    "line": 5,
                    "email": "blank@example.com",
                    "existing": False,
                    "previous_line": 4,
                }
            ],
        )

    def test_no_provider_alias_merging(self):
        rows = [
            {"line": 2, "email": "user+tag@example.com"},
            {"line": 3, "email": "user@example.com"},
            {"line": 4, "email": "user@sub.example.com"},
            {"line": 5, "email": "user@sub.example.com"},
        ]
        existing_emails = []

        result = detect_duplicate_emails(rows, existing_emails)

        self.assertEqual(
            result,
            [
                {
                    "line": 5,
                    "email": "user@sub.example.com",
                    "existing": False,
                    "previous_line": 4,
                }
            ],
        )

    def test_parser_row_composition(self):
        parser_rows = [
            {
                "line": 2,
                "name": "Alice", "email": "alice@example.com",
                "phone": "123", "company": "Example", "notes": "note",
            },
            {
                "line": 3,
                "name": "Bob", "email": "bob@example.com",
                "phone": "456", "company": "Example", "notes": "note",
            },
        ]
        existing_emails = ["alice@example.com"]

        result = detect_duplicate_emails(parser_rows, existing_emails)

        self.assertEqual(
            result,
            [
                {
                    "line": 2,
                    "email": "alice@example.com",
                    "existing": True,
                    "previous_line": None,
                }
            ],
        )

    def test_input_output_isolation(self):
        rows = [
            {"line": 2, "email": "isolated@example.com", "name": "Alice"},
            {"line": 3, "email": "isolated@example.com", "name": "Bob"},
        ]
        existing_emails = ["isolated@example.com"]
        original_rows = [dict(row) for row in rows]
        original_existing = list(existing_emails)

        result = detect_duplicate_emails(rows, existing_emails)

        self.assertEqual(rows, original_rows)
        self.assertEqual(existing_emails, original_existing)
        self.assertEqual(
            result,
            [
                {
                    "line": 2,
                    "email": "isolated@example.com",
                    "existing": True,
                    "previous_line": None,
                },
                {
                    "line": 3,
                    "email": "isolated@example.com",
                    "existing": True,
                    "previous_line": 2,
                },
            ],
        )
        self.assertNotIn("name", result[0])
        self.assertNotIn("name", result[1])

    def test_output_order_preserves_input_order(self):
        rows = [
            {"line": 10, "email": "order@example.com"},
            {"line": 2, "email": "order@example.com"},
            {"line": 7, "email": "order@example.com"},
        ]
        existing_emails = []

        result = detect_duplicate_emails(rows, existing_emails)

        self.assertEqual(
            result,
            [
                {
                    "line": 2,
                    "email": "order@example.com",
                    "existing": False,
                    "previous_line": 10,
                },
                {
                    "line": 7,
                    "email": "order@example.com",
                    "existing": False,
                    "previous_line": 10,
                },
            ],
        )

    def test_invalid_rows_raise_value_error(self):
        with self.assertRaises(ValueError):
            detect_duplicate_emails([{"line": 1, "email": "a@example.com"}], [])

        with self.assertRaises(ValueError):
            detect_duplicate_emails([{"line": True, "email": "a@example.com"}], [])

        with self.assertRaises(ValueError):
            detect_duplicate_emails([{"line": 2, "email": 123}], [])

        with self.assertRaises(ValueError):
            detect_duplicate_emails([{"line": 2, "email": "a@example.com"}], [123])

    def test_invalid_emails_raise_value_error(self):
        with self.assertRaises(ValueError):
            detect_duplicate_emails([{"line": 2, "email": "a@example"}], [])

        with self.assertRaises(ValueError):
            detect_duplicate_emails([{"line": 2, "email": "a@@example.com"}], [])

        with self.assertRaises(ValueError):
            detect_duplicate_emails([{"line": 2, "email": "a @example.com"}], [])

        with self.assertRaises(ValueError):
            detect_duplicate_emails([], ["a@example"])

    def test_exact_budgets_allowed(self):
        rows = [{"line": index + 2, "email": "exact@example.com"} for index in range(500)]
        existing_emails = ["exact@example.com"] * 20000

        result = detect_duplicate_emails(rows, existing_emails, max_rows=500, max_existing=20000)

        self.assertEqual(len(result), 500)
        self.assertEqual(result[0], {"line": 2, "email": "exact@example.com", "existing": True, "previous_line": None})
        self.assertEqual(result[1], {"line": 3, "email": "exact@example.com", "existing": True, "previous_line": 2})
        self.assertEqual(result[-1]["line"], 501)

    def test_over_budgets_raise_value_error(self):
        rows = [{"line": 2, "email": "over@example.com"}] * 501
        existing_emails = ["over@example.com"] * 20001

        with self.assertRaises(ValueError):
            detect_duplicate_emails(rows, existing_emails, max_rows=500, max_existing=20000)

        with self.assertRaises(ValueError):
            detect_duplicate_emails([], existing_emails, max_rows=500, max_existing=20000)

    def test_blanks_and_repeats_count_toward_budgets(self):
        rows = [{"line": 2, "email": ""}] * 501
        existing_emails = [""] * 20001

        with self.assertRaises(ValueError):
            detect_duplicate_emails(rows, existing_emails, max_rows=500, max_existing=20000)

        with self.assertRaises(ValueError):
            detect_duplicate_emails([], existing_emails, max_rows=500, max_existing=20000)

    def test_empty_and_no_conflict_data_return_empty_list(self):
        self.assertEqual(detect_duplicate_emails([], []), [])
        self.assertEqual(
            detect_duplicate_emails([{"line": 2, "email": "noconflict@example.com"}], []),
            [],
        )


if __name__ == "__main__":
    unittest.main()
