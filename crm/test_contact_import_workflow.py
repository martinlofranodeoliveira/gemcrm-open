from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from io import StringIO
from threading import Barrier
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.sessions.backends.db import SessionStore
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.db import DatabaseError, close_old_connections
from django.test import SimpleTestCase, TestCase, TransactionTestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .contact_import_workflow import (
    DRAFT_SESSION_KEY, ImportRejected, PreviewUnavailable, begin_preview, confirm_contacts,
    preview_contacts, save_preview,
)
from .forms import CONTACT_IMPORT_MAX_BYTES, ContactImportUploadForm
from .models import Company, Contact, ContactImportReceipt, ContactImportState


class ContactImportUploadTests(SimpleTestCase):
    def test_strict_utf8_and_size_are_checked_before_parsing(self):
        for content in (b"name\ninvalid\xff", b"x" * (CONTACT_IMPORT_MAX_BYTES + 1)):
            with self.subTest(size=len(content)):
                form = ContactImportUploadForm(files={"csv_file": SimpleUploadedFile("contacts.csv", content)})
                self.assertFalse(form.is_valid())
                self.assertIn("csv_file", form.errors)

    def test_utf8_bom_upload_decodes_without_replacement(self):
        content = "\ufeffname\nAção\n"
        form = ContactImportUploadForm(files={"csv_file": SimpleUploadedFile("contacts.csv", content.encode("utf-8"))})
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["csv_file"], content)


class ContactImportWorkflowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user("import-owner")
        cls.other = get_user_model().objects.create_user("import-other")
        cls.company = Company.objects.create(owner=cls.owner, name="Example Studio")

    def draft(self, text, owner=None):
        session = SessionStore()
        session["unrelated_session_value"] = "preserved"
        token = save_preview(session, owner or self.owner, text)
        session.save()
        return session, token

    def test_confirmation_creates_only_owned_contacts_and_consumes_blank_email_draft(self):
        text = "name,email,company\nExample,,Example Studio\nSecond,,\n"
        self.assertTrue(preview_contacts(self.owner, text)["valid"])
        self.assertEqual(Contact.objects.count(), 0)
        session, token = self.draft(text)
        self.assertEqual(confirm_contacts(session, self.owner, token), 2)
        self.assertEqual(Contact.objects.filter(owner=self.owner).count(), 2)
        self.assertEqual(Contact.objects.get(name="Example").company, self.company)
        self.assertEqual(session["unrelated_session_value"], "preserved")
        persisted = SessionStore(session_key=session.session_key)
        self.assertNotIn(DRAFT_SESSION_KEY, persisted)
        with self.assertRaises(PreviewUnavailable):
            confirm_contacts(persisted, self.owner, token)
        self.assertEqual(Contact.objects.count(), 2)

    def test_current_database_conflict_rejects_entire_batch_without_consuming_draft(self):
        text = "name,email\nFirst,first@example.com\nSecond,second@example.com\n"
        session, token = self.draft(text)
        Contact.objects.create(owner=self.owner, name="Competing record", email=" SECOND@example.com ")
        with self.assertRaises(ImportRejected) as caught:
            confirm_contacts(session, self.owner, token)
        self.assertEqual(caught.exception.preview["duplicate_lines"], [3])
        self.assertEqual(Contact.objects.count(), 1)
        self.assertIn(DRAFT_SESSION_KEY, SessionStore(session_key=session.session_key))

    def test_other_owner_duplicates_do_not_block_and_company_names_do_not_cross_accounts(self):
        Contact.objects.create(owner=self.other, name="Other contact", email="example@example.com")
        Company.objects.create(owner=self.other, name="Other company")
        valid = preview_contacts(self.owner, "name,email\nExample,example@example.com\n")
        self.assertTrue(valid["valid"])
        foreign = preview_contacts(self.owner, "name,company\nExample,Other company\n")
        self.assertFalse(foreign["valid"])
        self.assertTrue(foreign["errors"])
        Company.objects.create(owner=self.owner, name=self.company.name)
        ambiguous = preview_contacts(self.owner, "name,company\nExample,Example Studio\n")
        self.assertFalse(ambiguous["valid"])

    def test_model_field_validation_and_batch_duplicates_block_whole_preview(self):
        cases = [
            "name,email\nFirst,SAME@example.com\nSecond,same@example.com\n",
            "name\n" + "x" * 181 + "\n",
            "name,phone\nExample," + "1" * 41 + "\n",
            "name\n",
            "name\nNull\x00name\n",
        ]
        for text in cases:
            with self.subTest(text_length=len(text)):
                self.assertFalse(preview_contacts(self.owner, text)["valid"])
        self.assertEqual(Contact.objects.count(), 0)

    def test_company_ownership_is_rechecked_on_confirmation(self):
        text = "name,company\nExample,Example Studio\n"
        session, token = self.draft(text)
        Company.objects.filter(pk=self.company.pk).update(owner=self.other)
        with self.assertRaises(ImportRejected):
            confirm_contacts(session, self.owner, token)
        self.assertEqual(Contact.objects.count(), 0)

    def test_wrong_owner_or_expiry_cannot_consume_legitimate_preview(self):
        session, token = self.draft("name\nExample\n")
        with self.assertRaises(PreviewUnavailable):
            confirm_contacts(session, self.other, token)
        with self.assertRaises(PreviewUnavailable):
            confirm_contacts(session, self.owner, "invalid-non-ascii-ação")
        draft_time = session[DRAFT_SESSION_KEY]["created_at"]
        with patch("crm.contact_import_workflow.time.time", return_value=draft_time + 901):
            with self.assertRaises(PreviewUnavailable):
                confirm_contacts(session, self.owner, token)
        self.assertEqual(confirm_contacts(session, self.owner, token), 1)

    def test_save_error_rolls_back_entire_batch_and_token_consumption(self):
        session, token = self.draft("name\nFirst\nSecond\n")
        original_save = Contact.save

        def fail_on_second(instance, *args, **kwargs):
            if instance.name == "Second":
                raise DatabaseError("synthetic write failure")
            return original_save(instance, *args, **kwargs)

        with patch.object(Contact, "save", fail_on_second), self.assertRaises(DatabaseError):
            confirm_contacts(session, self.owner, token)
        self.assertEqual(Contact.objects.count(), 0)
        self.assertEqual(confirm_contacts(session, self.owner, token), 2)

    def test_confirmation_fails_closed_for_browser_stored_sessions(self):
        session, token = self.draft("name\nExample\n")
        with override_settings(SESSION_ENGINE="django.contrib.sessions.backends.signed_cookies"), self.assertRaises(PreviewUnavailable):
            confirm_contacts(session, self.owner, token)
        self.assertEqual(Contact.objects.count(), 0)


class ContactImportConcurrencyTests(TransactionTestCase):
    def test_simultaneous_confirmation_of_blank_email_draft_creates_once(self):
        owner = get_user_model().objects.create_user("parallel-import")
        session = SessionStore()
        token = save_preview(session, owner, "name\nExample\n")
        session.save()
        start = Barrier(2)

        def confirm_once():
            close_old_connections()
            try:
                thread_owner = get_user_model().objects.get(pk=owner.pk)
                thread_session = SessionStore(session_key=session.session_key)
                start.wait(timeout=10)
                try:
                    return confirm_contacts(thread_session, thread_owner, token)
                except (DatabaseError, PreviewUnavailable):
                    return 0
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            outcomes = list(executor.map(lambda _: confirm_once(), range(2)))
        self.assertLessEqual(sum(outcomes), 1)
        self.assertEqual(Contact.objects.count(), sum(outcomes))
        # SQLite may reject both colliding read-to-write upgrades. The draft
        # remains usable, so a subsequent request still creates exactly once.
        if not outcomes.count(1):
            self.assertEqual(confirm_contacts(SessionStore(session_key=session.session_key), owner, token), 1)
        self.assertEqual(Contact.objects.count(), 1)


class ContactImportReceiptTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user("receipt-owner")

    def draft(self, text="name\nBlank email contact\n"):
        session = SessionStore()
        token = save_preview(session, self.owner, text)
        session.save()
        return session, token

    def test_stale_session_save_cannot_resurrect_consumed_blank_email_preview(self):
        session, token = self.draft()
        stale_session = SessionStore(session_key=session.session_key)
        stale_session.items()  # Another request loads the old session first.
        original_created = stale_session[DRAFT_SESSION_KEY]["created_at"]
        self.assertEqual(confirm_contacts(session, self.owner, token), 1)
        stale_session["unrelated_change"] = "concurrent login/session response"
        stale_session.save()

        with self.assertRaises(PreviewUnavailable):
            confirm_contacts(SessionStore(session_key=session.session_key), self.owner, token)
        self.assertEqual(Contact.objects.count(), 1)
        receipt = ContactImportReceipt.objects.get()
        self.assertEqual(receipt.owner, self.owner)
        self.assertNotEqual(receipt.nonce_digest, token)
        self.assertNotEqual(receipt.session_digest, session.session_key)
        self.assertAlmostEqual(receipt.expires_at.timestamp(), original_created + 900, places=5)

    def test_failed_batch_rolls_back_receipt_and_allows_same_token_retry(self):
        session, token = self.draft("name\nFirst\nSecond\n")
        original_save = Contact.save

        def fail_second(instance, *args, **kwargs):
            if instance.name == "Second":
                raise DatabaseError("synthetic failure")
            return original_save(instance, *args, **kwargs)

        with patch.object(Contact, "save", fail_second), self.assertRaises(DatabaseError):
            confirm_contacts(session, self.owner, token)
        self.assertFalse(Contact.objects.exists())
        self.assertFalse(ContactImportReceipt.objects.exists())
        self.assertEqual(confirm_contacts(session, self.owner, token), 2)
        self.assertEqual(ContactImportReceipt.objects.count(), 1)

    def test_cleanup_preserves_active_receipts_and_expired_draft_cannot_replay_after_cleanup(self):
        session, token = self.draft()
        stale_session = SessionStore(session_key=session.session_key)
        stale_session.items()
        confirm_contacts(session, self.owner, token)
        output = StringIO()
        call_command("purge_contact_import_receipts", stdout=output)
        self.assertEqual(ContactImportReceipt.objects.count(), 1)
        self.assertEqual(ContactImportState.objects.count(), 1)
        self.assertIn("Removed 0", output.getvalue())

        expires_at = ContactImportReceipt.objects.get().expires_at
        after_expiry = expires_at + timedelta(seconds=1)
        stale_session["unrelated_change"] = "old response"
        stale_session.save()
        with patch("django.utils.timezone.now", return_value=after_expiry):
            call_command("purge_contact_import_receipts", stdout=StringIO())
        self.assertFalse(ContactImportReceipt.objects.exists())
        self.assertFalse(ContactImportState.objects.exists())
        with patch("crm.contact_import_workflow.time.time", return_value=after_expiry.timestamp()):
            with self.assertRaises(PreviewUnavailable):
                confirm_contacts(SessionStore(session_key=session.session_key), self.owner, token)
        self.assertEqual(Contact.objects.count(), 1)

    def test_future_and_nonfinite_preview_timestamps_never_create_receipts(self):
        for value in (timezone.now().timestamp() + 60, float("nan"), float("inf"), True):
            with self.subTest(value=value):
                session, token = self.draft()
                draft = session[DRAFT_SESSION_KEY]
                draft["created_at"] = value
                session[DRAFT_SESSION_KEY] = draft
                session.save()
                with self.assertRaises(PreviewUnavailable):
                    confirm_contacts(session, self.owner, token)
        self.assertFalse(Contact.objects.exists())
        self.assertFalse(ContactImportReceipt.objects.exists())

    def test_new_valid_upload_cannot_be_undone_by_stale_session_save(self):
        self.client.force_login(self.owner)
        first = self.client.post(reverse("crm:contact_import"), {
            "csv_file": SimpleUploadedFile("first.csv", b"name\nFirst batch\n"),
        })
        first_token = first.context["preview_token"]
        stale = SessionStore(session_key=self.client.session.session_key)
        stale.items()
        second = self.client.post(reverse("crm:contact_import"), {
            "csv_file": SimpleUploadedFile("second.csv", b"name\nSecond batch\n"),
        })
        self.assertTrue(second.context["preview_token"])
        stale["unrelated_change"] = "old request"
        stale.save()
        response = self.client.post(reverse("crm:contact_import_confirm"), {"preview_token": first_token})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Contact.objects.exists())
        self.assertFalse(ContactImportReceipt.objects.exists())

    def test_new_invalid_upload_cannot_be_undone_by_stale_session_save(self):
        self.client.force_login(self.owner)
        first = self.client.post(reverse("crm:contact_import"), {
            "csv_file": SimpleUploadedFile("first.csv", b"name\nFirst batch\n"),
        })
        first_token = first.context["preview_token"]
        stale = SessionStore(session_key=self.client.session.session_key)
        stale.items()
        invalid = self.client.post(reverse("crm:contact_import"), {
            "csv_file": SimpleUploadedFile("invalid.csv", b"name\nInvalid\xff\n"),
        })
        self.assertFalse(invalid.context["preview_token"])
        stale["unrelated_change"] = "old request"
        stale.save()
        response = self.client.post(reverse("crm:contact_import_confirm"), {"preview_token": first_token})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Contact.objects.exists())

    def test_older_upload_cannot_activate_after_newer_upload_started(self):
        session = SessionStore()
        older = begin_preview(session, self.owner)
        newer = begin_preview(session, self.owner)
        with self.assertRaises(PreviewUnavailable):
            save_preview(session, self.owner, "name\nOlder batch\n", attempt_token=older)
        save_preview(session, self.owner, "name\nNewer batch\n", attempt_token=newer)
        session.save()
        self.assertEqual(confirm_contacts(session, self.owner, newer), 1)
        self.assertEqual(Contact.objects.get().name, "Newer batch")
