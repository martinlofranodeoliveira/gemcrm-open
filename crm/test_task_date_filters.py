from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from crm.models import Task


class TaskDateFiltersTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="owner", password="pass12345")
        self.other = User.objects.create_user(username="other", password="pass12345")
        self.client.force_login(self.user)
        self.today = timezone.localdate()
        self.yesterday = self.today - timedelta(days=1)
        self.tomorrow = self.today + timedelta(days=1)
        self.open_today = Task.objects.create(owner=self.user, title="hoje aberta", due_date=self.today, completed=False)
        self.done_today = Task.objects.create(owner=self.user, title="hoje concluida", due_date=self.today, completed=True)
        self.overdue = Task.objects.create(owner=self.user, title="atrasada aberta", due_date=self.yesterday, completed=False)
        self.upcoming = Task.objects.create(owner=self.user, title="futura aberta", due_date=self.tomorrow, completed=False)
        self.done_future = Task.objects.create(owner=self.user, title="futura concluida", due_date=self.tomorrow, completed=True)
        self.other_today = Task.objects.create(owner=self.other, title="hoje outro dono", due_date=self.today, completed=False)

    def get_titles(self, query=""):
        response = self.client.get(reverse("crm:tasks") + query)
        self.assertEqual(response.status_code, 200)
        return {item.title for item in response.context["items"]}

    def test_today_returns_only_open_due_today_for_owner(self):
        titles = self.get_titles("?status=today")
        self.assertIn(self.open_today.title, titles)
        self.assertNotIn(self.done_today.title, titles)
        self.assertNotIn(self.overdue.title, titles)
        self.assertNotIn(self.upcoming.title, titles)
        self.assertNotIn(self.done_future.title, titles)
        self.assertNotIn(self.other_today.title, titles)

    def test_upcoming_uses_strictly_future_open_tasks(self):
        titles = self.get_titles("?status=upcoming")
        self.assertIn(self.upcoming.title, titles)
        self.assertNotIn(self.open_today.title, titles)
        self.assertNotIn(self.done_future.title, titles)
        self.assertNotIn(self.overdue.title, titles)
        self.assertNotIn(self.done_today.title, titles)

    def test_search_q_combines_with_date_filters(self):
        Task.objects.create(owner=self.user, title="retorno cliente", due_date=self.today, completed=False)
        Task.objects.create(owner=self.user, title="outra rotina", due_date=self.today, completed=False)
        titles = self.get_titles("?status=today&q=retorno")
        self.assertIn("retorno cliente", titles)
        self.assertNotIn("outra rotina", titles)
        self.assertNotIn(self.upcoming.title, titles)
        upcoming_titles = self.get_titles("?status=upcoming&q=futura")
        self.assertIn(self.upcoming.title, upcoming_titles)

    def test_legacy_statuses_and_fallback_preserved(self):
        open_titles = self.get_titles("?status=open")
        self.assertIn(self.open_today.title, open_titles)
        self.assertIn(self.overdue.title, open_titles)
        self.assertIn(self.upcoming.title, open_titles)
        self.assertNotIn(self.done_today.title, open_titles)
        overdue_titles = self.get_titles("?status=overdue")
        self.assertIn(self.overdue.title, overdue_titles)
        self.assertNotIn(self.open_today.title, overdue_titles)
        self.assertNotIn(self.upcoming.title, overdue_titles)
        completed_titles = self.get_titles("?status=completed")
        self.assertIn(self.done_today.title, completed_titles)
        self.assertIn(self.done_future.title, completed_titles)
        self.assertNotIn(self.open_today.title, completed_titles)
        fallback = self.client.get(reverse("crm:tasks") + "?status=invalido")
        self.assertEqual(fallback.status_code, 200)
        self.assertEqual(fallback.context["status"], "all")
        fallback_titles = {item.title for item in fallback.context["items"]}
        self.assertIn(self.open_today.title, fallback_titles)
        self.assertIn(self.done_today.title, fallback_titles)

    def test_filters_do_not_write_records(self):
        before = list(Task.objects.order_by("pk").values("pk", "title", "due_date", "completed", "owner_id"))
        self.get_titles("?status=today")
        self.get_titles("?status=upcoming")
        self.get_titles("?status=today&q=hoje")
        after = list(Task.objects.order_by("pk").values("pk", "title", "due_date", "completed", "owner_id"))
        self.assertEqual(before, after)

    def test_form_contains_today_upcoming_and_keeps_selection(self):
        for status in ("today", "upcoming"):
            response = self.client.get(reverse("crm:tasks") + f"?status={status}")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context["status"], status)
            content = response.content.decode()
            self.assertIn('value="today"', content)
            self.assertIn('value="upcoming"', content)
            self.assertIn(f'value="{status}" selected', content)
