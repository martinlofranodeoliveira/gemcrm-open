import csv
from datetime import timedelta
from decimal import Decimal
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError, transaction
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from .forms import ContactForm, DealForm, TaskForm
from .models import Company, Contact, Deal, Task


class CrmTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user("owner", password="Zephyr47!GardenRiver")
        cls.other = get_user_model().objects.create_user("other", password="Zephyr47!GardenRiver")
        cls.company = Company.objects.create(owner=cls.owner, name="Ateliê Horizonte", website="https://example.com")
        cls.other_company = Company.objects.create(owner=cls.other, name="Empresa confidencial")
        cls.contact = Contact.objects.create(owner=cls.owner, name="Ana Exemplo", email="ana@example.com", company=cls.company)
        cls.other_contact = Contact.objects.create(owner=cls.other, name="Contato confidencial", company=cls.other_company)
        cls.deal = Deal.objects.create(owner=cls.owner, title="Site do ateliê", company=cls.company, contact=cls.contact, value=Decimal("1200.50"))
        cls.other_deal = Deal.objects.create(owner=cls.other, title="Oportunidade confidencial", value=Decimal("999999.00"))
        cls.task = Task.objects.create(owner=cls.owner, title="Preparar proposta", deal=cls.deal, due_date=timezone.localdate())
        cls.other_task = Task.objects.create(owner=cls.other, title="Tarefa confidencial", due_date=timezone.localdate())

    def setUp(self):
        self.client.force_login(self.owner)

    def test_anonymous_requests_redirect_to_login(self):
        self.client.logout()
        names = ["dashboard", "companies", "contacts", "deals", "tasks", "contact_export", "company_create", "contact_create", "deal_create", "task_create"]
        for name in names:
            with self.subTest(name=name):
                response = self.client.get(reverse(f"crm:{name}"))
                self.assertEqual(response.status_code, 302)
                self.assertTrue(response.url.startswith(reverse("login")))

    def test_dashboard_totals_exclude_other_users_and_closed_deals(self):
        Deal.objects.create(owner=self.owner, title="Venda ganha", value=Decimal("50.00"), stage=Deal.Stage.WON)
        Deal.objects.create(owner=self.owner, title="Venda perdida", value=Decimal("70.00"), stage=Deal.Stage.LOST)
        Task.objects.create(owner=self.owner, title="Amanhã", due_date=timezone.localdate() + timedelta(days=1))
        response = self.client.get(reverse("crm:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["company_count"], 1)
        self.assertEqual(response.context["contact_count"], 1)
        self.assertEqual(response.context["open_deal_count"], 1)
        self.assertEqual(response.context["pipeline_value"], Decimal("1200.50"))
        self.assertEqual(list(response.context["due_tasks"]), [self.task])
        self.assertNotContains(response, "confidencial")

    def test_list_pages_are_owner_scoped(self):
        for name, expected in [("companies", self.company), ("contacts", self.contact), ("tasks", self.task)]:
            with self.subTest(name=name):
                response = self.client.get(reverse(f"crm:{name}"))
                self.assertEqual(response.status_code, 200)
                self.assertEqual(list(response.context["items"]), [expected])
                self.assertNotContains(response, "confidencial")
        response = self.client.get(reverse("crm:deals"))
        rows = [item for column in response.context["columns"] for item in column["deals"]]
        self.assertEqual(rows, [self.deal])

    def test_search_is_scoped_and_matches_related_company(self):
        response = self.client.get(reverse("crm:contacts"), {"q": "Horizonte"})
        self.assertEqual(list(response.context["items"]), [self.contact])
        response = self.client.get(reverse("crm:contacts"), {"q": "confidencial"})
        self.assertEqual(list(response.context["items"]), [])
        response = self.client.get(reverse("crm:deals"), {"q": "Horizonte"})
        self.assertEqual(response.context["columns"][0]["deals"], [self.deal])

    def test_other_users_records_cannot_be_read_updated_or_deleted(self):
        records = [("company", self.other_company), ("contact", self.other_contact), ("deal", self.other_deal), ("task", self.other_task)]
        for prefix, record in records:
            for action in ["update", "delete"]:
                url = reverse(f"crm:{prefix}_{action}", args=[record.pk])
                for method in ["get", "post"]:
                    with self.subTest(prefix=prefix, action=action, method=method):
                        self.assertEqual(getattr(self.client, method)(url).status_code, 404)
                self.assertTrue(type(record).objects.filter(pk=record.pk).exists())

    def test_company_create_uses_authenticated_owner_ignoring_submitted_owner(self):
        response = self.client.post(reverse("crm:company_create"), {"name": "Nova empresa", "website": "", "notes": "", "owner": self.other.pk})
        self.assertRedirects(response, reverse("crm:companies"))
        self.assertEqual(Company.objects.get(name="Nova empresa").owner, self.owner)

    def test_company_edit_does_not_change_owner(self):
        response = self.client.post(reverse("crm:company_update", args=[self.company.pk]), {"name": "Ateliê atualizado", "website": "", "notes": "", "owner": self.other.pk})
        self.assertRedirects(response, reverse("crm:companies"))
        self.company.refresh_from_db()
        self.assertEqual(self.company.name, "Ateliê atualizado")
        self.assertEqual(self.company.owner, self.owner)

    def test_related_choices_exclude_other_accounts(self):
        contact_form = ContactForm(owner=self.owner)
        deal_form = DealForm(owner=self.owner)
        task_form = TaskForm(owner=self.owner)
        self.assertEqual(list(contact_form.fields["company"].queryset), [self.company])
        self.assertEqual(list(deal_form.fields["contact"].queryset), [self.contact])
        self.assertEqual(list(task_form.fields["deal"].queryset), [self.deal])

    def test_contact_cannot_reference_other_users_company(self):
        form = ContactForm({"name": "Tentativa", "company": self.other_company.pk}, owner=self.owner)
        self.assertFalse(form.is_valid())
        self.assertIn("company", form.errors)
        response = self.client.post(reverse("crm:contact_create"), {"name": "Tentativa", "company": self.other_company.pk})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Contact.objects.filter(name="Tentativa").exists())

    def test_deal_cannot_reference_other_users_contacts_or_company(self):
        form = DealForm({"title": "Tentativa", "value": "10.00", "stage": "new", "company": self.other_company.pk, "contact": self.other_contact.pk}, owner=self.owner)
        self.assertFalse(form.is_valid())
        self.assertIn("company", form.errors)
        self.assertIn("contact", form.errors)

    def test_task_cannot_reference_other_users_deal(self):
        form = TaskForm({"title": "Tentativa", "due_date": "2026-10-18", "deal": self.other_deal.pk}, owner=self.owner)
        self.assertFalse(form.is_valid())
        self.assertIn("deal", form.errors)

    def test_model_validation_rejects_cross_account_relationships(self):
        objects = [
            Contact(owner=self.owner, name="Tentativa", company=self.other_company),
            Deal(owner=self.owner, title="Tentativa", contact=self.other_contact),
            Task(owner=self.owner, title="Tentativa", due_date=timezone.localdate(), deal=self.other_deal),
        ]
        for obj in objects:
            with self.subTest(model=type(obj).__name__), self.assertRaises(ValidationError):
                obj.full_clean()

    def test_negative_deal_value_is_rejected_by_database(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Deal.objects.create(owner=self.owner, title="Inválida", value=Decimal("-1.00"))

    def test_deal_stage_change_requires_post_and_valid_choice(self):
        url = reverse("crm:deal_stage", args=[self.deal.pk])
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(self.client.post(url, {"stage": "invented"}).status_code, 400)
        self.deal.refresh_from_db()
        self.assertEqual(self.deal.stage, Deal.Stage.NEW)
        self.assertRedirects(self.client.post(url, {"stage": "won"}), reverse("crm:deals"))
        self.deal.refresh_from_db()
        self.assertEqual(self.deal.stage, Deal.Stage.WON)

    def test_other_users_deal_and_task_cannot_be_mutated(self):
        self.assertEqual(self.client.post(reverse("crm:deal_stage", args=[self.other_deal.pk]), {"stage": "won"}).status_code, 404)
        self.assertEqual(self.client.post(reverse("crm:task_toggle", args=[self.other_task.pk])).status_code, 404)
        self.other_deal.refresh_from_db()
        self.other_task.refresh_from_db()
        self.assertEqual(self.other_deal.stage, Deal.Stage.NEW)
        self.assertFalse(self.other_task.completed)

    def test_task_toggle_and_status_filter(self):
        url = reverse("crm:task_toggle", args=[self.task.pk])
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertRedirects(self.client.post(url), reverse("crm:tasks"))
        self.task.refresh_from_db()
        self.assertTrue(self.task.completed)
        self.assertEqual(list(self.client.get(reverse("crm:tasks"), {"status": "open"}).context["items"]), [])
        self.assertEqual(list(self.client.get(reverse("crm:tasks"), {"status": "completed"}).context["items"]), [self.task])

    def test_delete_requires_post_and_keeps_related_records(self):
        url = reverse("crm:company_delete", args=[self.company.pk])
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertTrue(Company.objects.filter(pk=self.company.pk).exists())
        self.assertRedirects(self.client.post(url), reverse("crm:companies"))
        self.contact.refresh_from_db()
        self.deal.refresh_from_db()
        self.assertIsNone(self.contact.company_id)
        self.assertIsNone(self.deal.company_id)

    def test_csv_export_only_contains_current_users_search_results(self):
        response = self.client.get(reverse("crm:contact_export"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")
        rows = list(csv.reader(StringIO(response.content.decode("utf-8-sig"))))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1][0], self.contact.name)
        self.assertEqual(rows[1][3], self.company.name)
        self.assertNotIn("confidencial", response.content.decode())
        response = self.client.get(reverse("crm:contact_export"), {"q": "missing"})
        self.assertEqual(len(list(csv.reader(StringIO(response.content.decode("utf-8-sig"))))), 1)

    def test_csv_cells_cannot_execute_spreadsheet_formulas(self):
        Contact.objects.create(owner=self.owner, name="=1+1", email="test@example.com", phone="+5511999999999", notes="  @SUM(1,1)")
        response = self.client.get(reverse("crm:contact_export"), {"q": "test@example.com"})
        rows = list(csv.reader(StringIO(response.content.decode("utf-8-sig"))))
        self.assertEqual(rows[1][0], "'=1+1")
        self.assertEqual(rows[1][2], "'+5511999999999")
        self.assertEqual(rows[1][4], "'  @SUM(1,1)")

    def test_user_input_is_html_escaped(self):
        self.contact.name = '<script>alert("test")</script>'
        self.contact.save()
        response = self.client.get(reverse("crm:contacts"))
        self.assertNotContains(response, '<script>alert("test")</script>')
        self.assertContains(response, "&lt;script&gt;")

    def test_csrf_is_enforced_for_mutations(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.owner)
        self.assertEqual(client.post(reverse("crm:task_toggle", args=[self.task.pk])).status_code, 403)
        self.task.refresh_from_db()
        self.assertFalse(self.task.completed)


class AuthenticationTests(TestCase):
    def test_signup_creates_authenticated_account(self):
        response = self.client.post(reverse("signup"), {"username": "new-account", "email": "person@example.com", "password1": "Zephyr47!GardenRiver", "password2": "Zephyr47!GardenRiver"})
        self.assertRedirects(response, reverse("crm:dashboard"))
        user = get_user_model().objects.get(username="new-account")
        self.assertEqual(user.email, "person@example.com")
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_signup_rejects_weak_password(self):
        response = self.client.post(reverse("signup"), {"username": "new-account", "password1": "123", "password2": "123"})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(get_user_model().objects.exists())

    def test_login_works_and_logout_requires_post(self):
        user = get_user_model().objects.create_user("member", password="Zephyr47!GardenRiver")
        response = self.client.post(reverse("login"), {"username": user.username, "password": "Zephyr47!GardenRiver"})
        self.assertRedirects(response, reverse("crm:dashboard"))
        self.assertEqual(self.client.get(reverse("logout")).status_code, 405)
        self.assertRedirects(self.client.post(reverse("logout")), reverse("login"))
        self.assertNotIn("_auth_user_id", self.client.session)


class DemoCommandTests(TestCase):
    def test_demo_requires_existing_empty_account_and_does_not_create_password(self):
        with self.assertRaises(CommandError):
            call_command("seed_demo", username="missing", stdout=StringIO())
        owner = get_user_model().objects.create_user("demo", password=None)
        password_before = owner.password
        call_command("seed_demo", username="demo", stdout=StringIO())
        owner.refresh_from_db()
        self.assertEqual(owner.password, password_before)
        self.assertEqual(Company.objects.filter(owner=owner).count(), 4)
        self.assertEqual(Contact.objects.filter(owner=owner).count(), 4)
        self.assertEqual(Deal.objects.filter(owner=owner).count(), 6)
        self.assertEqual(Task.objects.filter(owner=owner).count(), 5)
        with self.assertRaises(CommandError):
            call_command("seed_demo", username="demo", stdout=StringIO())
