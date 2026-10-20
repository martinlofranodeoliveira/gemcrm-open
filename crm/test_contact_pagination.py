from django.contrib.auth.models import User
from django.http import QueryDict
from django.test import TestCase
from django.urls import reverse
from django.utils.html import escape
from django.utils.http import urlencode
from html.parser import HTMLParser

from crm.models import Company, Contact


class NavParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_nav = False
        self.nav_count = 0
        self.nav_text = ""
        self.links = []
        self._cur = None

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == "nav" and d.get("aria-label") == "Paginação de contatos":
            self.in_nav = True
            self.nav_count += 1
        if self.in_nav and tag == "a":
            cur = {"href": d.get("href", ""), "rel": d.get("rel", ""), "text": ""}
            self.links.append(cur)
            self._cur = cur

    def handle_endtag(self, tag):
        if tag == "nav" and self.in_nav:
            self.in_nav = False
        if tag == "a":
            self._cur = None

    def handle_data(self, data):
        if self.in_nav:
            self.nav_text += data
        if self._cur is not None:
            self._cur["text"] += data


class ContactPaginationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="owner", password="pass12345")
        self.other = User.objects.create_user(username="other", password="pass12345")
        self.client.force_login(self.user)
        self.url = reverse("crm:contacts")
        self.export_url = reverse("crm:contact_export")

    def make_contact(self, owner, name, email="", phone="", company=None, notes=""):
        return Contact.objects.create(owner=owner, name=name, email=email, phone=phone, company=company, notes=notes)

    def make_many(self, owner, count, prefix="Contato"):
        for i in range(count):
            self.make_contact(owner, f"{prefix} {i:04d}")

    def get_page(self, query=""):
        response = self.client.get(self.url + query)
        self.assertEqual(response.status_code, 200)
        return response

    def test_first_and_second_page_counts(self):
        self.make_many(self.user, 55, prefix="Base")
        r1 = self.get_page("?" + urlencode({"page": 1}))
        self.assertEqual(len(list(r1.context["items"])), 50)
        self.assertEqual(r1.context["page_obj"].number, 1)
        self.assertEqual(r1.context["page_obj"].paginator.num_pages, 2)
        self.assertEqual(r1.context["page_obj"].paginator.count, 55)
        r2 = self.get_page("?" + urlencode({"page": 2}))
        self.assertEqual(len(list(r2.context["items"])), 5)
        self.assertEqual(r2.context["page_obj"].number, 2)
        self.assertEqual(list(r2.context["items"]), list(r2.context["page_obj"].object_list))
        self.assertEqual(list(r1.context["items"]), list(r1.context["page_obj"].object_list))

    def test_ordering_name_pk_ascending(self):
        self.make_contact(self.user, "Zebra")
        self.make_contact(self.user, "Abacate")
        self.make_contact(self.user, "Manga")
        resp = self.get_page()
        names = [c.name for c in resp.context["items"]]
        self.assertEqual(names, sorted(names))

    def test_name_pk_tie_break_across_pages(self):
        for _ in range(52):
            self.make_contact(self.user, "Repetido")
        r1 = self.get_page("?" + urlencode({"page": 1}))
        r2 = self.get_page("?" + urlencode({"page": 2}))
        pks1 = [c.pk for c in r1.context["items"]]
        pks2 = [c.pk for c in r2.context["items"]]
        self.assertEqual(len(pks1), 50)
        self.assertEqual(len(pks2), 2)
        self.assertEqual(pks1, sorted(pks1))
        self.assertEqual(pks2, sorted(pks2))
        self.assertLess(max(pks1), min(pks2))
        all_pks = pks1 + pks2
        self.assertEqual(all_pks, sorted(all_pks))

    def test_search_combines_fields_and_paginates(self):
        comp = Company.objects.create(owner=self.user, name="Acme Busca")
        self.make_contact(self.user, "Alvo Nome", email="x1@example.com")
        self.make_contact(self.user, "Outro", email="alvo@example.com")
        self.make_contact(self.user, "Fone", phone="999-alvo-000")
        self.make_contact(self.user, "Ligado", company=comp)
        self.make_contact(self.user, "Fora", email="fora@example.com")
        for q in ["alvo", "ALVO", "Acme Busca"]:
            resp = self.get_page("?" + urlencode({"q": q}))
            names = {c.name for c in resp.context["items"]}
            if q.lower() != "acme busca":
                self.assertIn("Alvo Nome", names)
            if q.lower() == "acme busca":
                self.assertIn("Ligado", names)
                self.assertNotIn("Fora", names)
        resp = self.get_page("?" + urlencode({"q": "  alvo  "}))
        self.assertEqual(resp.context["q"], "alvo")
        self.assertIn("Alvo Nome", {c.name for c in resp.context["items"]})

    def test_page_fallbacks(self):
        self.make_many(self.user, 55, prefix="Pag")
        for query, expected in [("", 1), ("?" + urlencode({"page": ""}), 1), ("?" + urlencode({"page": "abc"}), 1), ("?" + urlencode({"page": "1.5"}), 1)]:
            resp = self.get_page(query)
            self.assertEqual(resp.context["page_obj"].number, expected)
        for query in ["?" + urlencode({"page": "0"}), "?" + urlencode({"page": "-2"}), "?" + urlencode({"page": "99"})]:
            resp = self.get_page(query)
            self.assertEqual(resp.context["page_obj"].number, 2)
        resp = self.get_page("?" + urlencode({"q": "nenhum-tal-xyz"}))
        self.assertEqual(len(list(resp.context["items"])), 0)
        self.assertEqual(resp.context["page_obj"].number, 1)
        self.assertEqual(resp.context["page_obj"].paginator.num_pages, 1)
        self.assertIn("Nenhum contato encontrado", resp.content.decode())

    def test_get_does_not_write(self):
        self.make_many(self.user, 3, prefix="Keep")
        before = list(Contact.objects.order_by("pk").values("pk", "name", "email", "phone", "owner_id"))
        self.get_page()
        self.get_page("?" + urlencode({"page": "2", "q": "Keep"}))
        after = list(Contact.objects.order_by("pk").values("pk", "name", "email", "phone", "owner_id"))
        self.assertEqual(before, after)

    def test_isolation_totals_only_owner(self):
        self.make_many(self.user, 55, prefix="Mine")
        self.make_many(self.other, 30, prefix="Mine")
        r1 = self.get_page()
        self.assertEqual(r1.context["page_obj"].paginator.count, 55)
        self.assertEqual(r1.context["page_obj"].paginator.num_pages, 2)
        for c in r1.context["items"]:
            self.assertEqual(c.owner_id, self.user.pk)
        r2 = self.get_page("?" + urlencode({"page": 2}))
        for c in r2.context["items"]:
            self.assertEqual(c.owner_id, self.user.pk)

    def test_navigation_links_and_text(self):
        self.make_many(self.user, 55, prefix="Nav")
        r1 = self.get_page("?" + urlencode({"page": 1}))
        p1 = NavParser()
        p1.feed(r1.content.decode())
        self.assertEqual(p1.nav_count, 1)
        self.assertIn("Página 1 de 2", p1.nav_text)
        rels1 = {l["rel"] for l in p1.links}
        self.assertNotIn("prev", rels1)
        self.assertIn("next", rels1)
        nxt = [l for l in p1.links if l["rel"] == "next"][0]
        qd = QueryDict(nxt["href"].split("?", 1)[1] if "?" in nxt["href"] else "")
        self.assertEqual(set(qd.keys()), {"page"})
        self.assertEqual(qd.get("page"), "2")
        self.assertTrue(nxt["href"].startswith("/contacts/"))
        r2 = self.get_page("?" + urlencode({"page": 2}))
        p2 = NavParser()
        p2.feed(r2.content.decode())
        self.assertIn("Página 2 de 2", p2.nav_text)
        rels2 = {l["rel"] for l in p2.links}
        self.assertIn("prev", rels2)
        self.assertNotIn("next", rels2)
        prv = [l for l in p2.links if l["rel"] == "prev"][0]
        qd2 = QueryDict(prv["href"].split("?", 1)[1] if "?" in prv["href"] else "")
        self.assertEqual(qd2.get("page"), "1")
        rq = self.get_page("?" + urlencode({"q": "Nav", "page": "2"}))
        pq = NavParser()
        pq.feed(rq.content.decode())
        self.assertIn("Página 2 de 2", pq.nav_text)
        for link in pq.links:
            qd3 = QueryDict(link["href"].split("?", 1)[1])
            self.assertEqual(qd3.get("q"), "Nav")
            self.assertIn("page", qd3.keys())
            self.assertEqual(set(qd3.keys()), {"page", "q"})
        self.assertNotIn('name="page"', rq.content.decode())
        single = NavParser()
        resp_single = self.get_page("?" + urlencode({"q": "Nav 0001"}))
        single.feed(resp_single.content.decode())
        self.assertEqual(single.nav_count, 0)

    def test_escaping_and_encoded_query(self):
        special = "A&B <C> \"Q\" 'S' +/=? Ünïcødé"
        self.make_contact(self.user, special, email="e@example.com")
        resp = self.get_page("?" + urlencode({"q": special}))
        content = resp.content.decode()
        self.assertIn(escape(special), content)
        self.assertNotIn(special.replace("&", "&amp;").replace("<", "<"), content) if "<C>" in special else None
        self.assertIn("&amp;", content)
        self.assertIn("&lt;", content)
        q = QueryDict(urlencode({"q": special, "page": "1"}))
        self.assertEqual(q.get("q"), special)
        resp2 = self.get_page("?" + urlencode({"q": special}))
        self.assertEqual(resp2.context["q"], special)
        self.assertIn(special, [c.name for c in resp2.context["items"]])

    def test_csv_exports_all_filtered_ignoring_page(self):
        self.make_many(self.user, 55, prefix="CsvAll")
        self.make_many(self.other, 10, prefix="CsvAll")
        resp = self.client.get(self.export_url + "?" + urlencode({"page": "2"}))
        self.assertEqual(resp.status_code, 200)
        text = resp.content.decode("utf-8-sig")
        self.assertIn("CsvAll", text)
        lines = [ln for ln in text.splitlines() if "CsvAll" in ln]
        self.assertEqual(len(lines), 55)
        resp_q = self.client.get(self.export_url + "?" + urlencode({"q": "CsvAll 0001", "page": "2"}))
        text_q = resp_q.content.decode("utf-8-sig")
        self.assertIn("CsvAll 0001", text_q)
        self.assertNotIn("CsvAll 0002", text_q)
