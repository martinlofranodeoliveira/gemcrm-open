import unittest

from crm.contact_import import parse_contacts


class ContactImportPreviewTests(unittest.TestCase):
    def test_normal_contacts(self):
        result = parse_contacts(
            "name,email,phone,company,notes\n"
            "Alice,alice@example.com,123,Example Corp,hello\n"
            "Bob,bob@example.com,,Example Inc,\n"
        )

        self.assertEqual(result["valid"], True)
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["rows"], [
            {
                "line": 2,
                "name": "Alice",
                "email": "alice@example.com",
                "phone": "123",
                "company": "Example Corp",
                "notes": "hello",
            },
            {
                "line": 3,
                "name": "Bob",
                "email": "bob@example.com",
                "phone": "",
                "company": "Example Inc",
                "notes": "",
            },
        ])

    def test_supports_leading_bom(self):
        result = parse_contacts(
            "\ufeffname,email\n"
            "Alice,alice@example.com\n"
        )

        self.assertEqual(result["valid"], True)
        self.assertEqual(result["rows"][0]["line"], 2)
        self.assertEqual(result["rows"][0]["name"], "Alice")
        self.assertEqual(result["rows"][0]["email"], "alice@example.com")

    def test_quoted_commas_and_newlines(self):
        result = parse_contacts(
            "name,notes\n"
            "\"Alice\",\"hello, world\"\n"
            "\"Bob\",\"line one\nline two\"\n"
        )

        self.assertEqual(result["valid"], True)
        self.assertEqual(result["rows"][0]["name"], "Alice")
        self.assertEqual(result["rows"][0]["notes"], "hello, world")
        self.assertEqual(result["rows"][1]["name"], "Bob")
        self.assertEqual(result["rows"][1]["notes"], "line one\nline two")

    def test_blank_optional_fields_are_allowed(self):
        result = parse_contacts(
            "name,email,phone,company,notes\n"
            "Alice,,,,\n"
        )

        self.assertEqual(result["valid"], True)
        self.assertEqual(result["rows"][0]["email"], "")
        self.assertEqual(result["rows"][0]["phone"], "")
        self.assertEqual(result["rows"][0]["company"], "")
        self.assertEqual(result["rows"][0]["notes"], "")

    def test_empty_input_is_invalid(self):
        result = parse_contacts("")

        self.assertEqual(result["valid"], False)
        self.assertEqual(result["rows"], [])
        self.assertEqual(result["errors"], [{"line": 1, "message": "Header is required"}])

    def test_missing_name_header_is_invalid(self):
        result = parse_contacts("email\n")

        self.assertEqual(result["valid"], False)
        self.assertEqual(result["errors"], [{"line": 1, "message": "Header must include name"}])

    def test_duplicate_header_is_invalid(self):
        result = parse_contacts("name,name\n")

        self.assertEqual(result["valid"], False)
        self.assertEqual(result["errors"], [{"line": 1, "message": "Duplicate header column"}])

    def test_unknown_header_is_invalid(self):
        result = parse_contacts("name,unknown\n")

        self.assertEqual(result["valid"], False)
        self.assertEqual(result["errors"], [{"line": 1, "message": "Unknown header column"}])

    def test_invalid_email_is_rejected(self):
        result = parse_contacts(
            "name,email\n"
            "Alice,alice@example.com\n"
            "Bob,bad email\n"
            "Carol,a@example..com\n"
            "Dave,a@.example.com\n"
        )

        self.assertEqual(result["valid"], False)
        self.assertEqual(result["rows"], [
            {
                "line": 2,
                "name": "Alice",
                "email": "alice@example.com",
                "phone": "",
                "company": "",
                "notes": "",
            }
        ])
        self.assertEqual(result["errors"], [
            {"line": 3, "message": "Invalid email"},
            {"line": 4, "message": "Invalid email"},
            {"line": 5, "message": "Invalid email"},
        ])

    def test_missing_name_is_rejected(self):
        result = parse_contacts(
            "name,email\n"
            ",alice@example.com\n"
        )

        self.assertEqual(result["valid"], False)
        self.assertEqual(result["errors"], [{"line": 2, "message": "Name is required"}])

    def test_malformed_csv_is_rejected(self):
        result = parse_contacts(
            "name,notes\n"
            "Alice,\"unclosed\n"
        )

        self.assertEqual(result["valid"], False)
        self.assertEqual(result["errors"], [{"line": 2, "message": "Malformed CSV"}])

    def test_row_width_mismatch_is_rejected(self):
        result = parse_contacts(
            "name,email\n"
            "Alice,alice@example.com\n"
            "Bob\n"
        )

        self.assertEqual(result["valid"], False)
        self.assertEqual(result["errors"], [{"line": 3, "message": "Row width mismatch"}])

    def test_overflow_is_reported_and_not_returned(self):
        result = parse_contacts(
            "name\n"
            "Alice\n"
            "Bob\n"
            "Carol\n",
            max_rows=2,
        )

        self.assertEqual(result["valid"], False)
        self.assertEqual(result["rows"], [
            {"line": 2, "name": "Alice", "email": "", "phone": "", "company": "", "notes": ""},
            {"line": 3, "name": "Bob", "email": "", "phone": "", "company": "", "notes": ""},
        ])
        self.assertEqual(result["errors"], [{"line": 4, "message": "Row limit exceeded"}])

    def test_non_string_input_raises_value_error(self):
        with self.assertRaises(ValueError):
            parse_contacts(None)

    def test_invalid_max_rows_raises_value_error(self):
        with self.assertRaises(ValueError):
            parse_contacts("name\n", max_rows=0)


if __name__ == "__main__":
    unittest.main()
