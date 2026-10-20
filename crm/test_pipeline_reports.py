import csv
import io
from decimal import Decimal
from html.parser import HTMLParser

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from crm.models import Deal


class TableCounter(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.row_th = 0
        self.col_th = 0

    def handle_starttag(self, tag, attrs):
        if tag == "th":
            d = dict(attrs)
            if d.get("scope") == "row":
                self.row_th += 1
            if d.get("scope") == "col":
                self.col_th += 1


class PipelineReportTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="pass12345")
        self.other = User.objects.create_user(username="other", password="pass12345")
        self.client.force_login(self.owner)
        self.report = reverse("crm:pipeline_report")
        self.export = reverse("crm:pipeline_report_export")
        self.deals_url = reverse("crm:deals")

    def _mk(self, owner, stage, value, expected_close=None):
        title = "T %s %s %s" % (stage, value, expected_close)
        return Deal.objects.create(owner=owner, title=title, stage=stage, value=Decimal(value), expected_close=expected_close)

    def test_login_and_get_only(self):
        self.client.logout()
        r = self.client.get(self.report)
        self.assertEqual(r.status_code, 302)
        self.assertIn("/accounts/login", r["Location"])
        e = self.client.get(self.export)
        self.assertEqual(e.status_code, 302)
        self.assertIn("/accounts/login", e["Location"])
        self.client.force_login(self.owner)
        for method in [self.client.post, self.client.put, self.client.delete]:
            rr = method(self.report)
            self.assertEqual(rr.status_code, 405)
            self.assertIn("GET", rr["Allow"])
            ee = method(self.export)
            self.assertEqual(ee.status_code, 405)
            self.assertIn("GET", ee["Allow"])
        self.assertEqual(self.client.get(self.report).status_code, 200)
        self.assertEqual(self.client.get(self.export).status_code, 200)

    def test_isolation(self):
        self._mk(self.other, "new", "50.00", None)
        self._mk(self.owner, "new", "10.00", None)
        r = self.client.get(self.report)
        body = r.content.decode()
        self.assertIn("R$ 10,00", body)
        self.assertNotIn("R$ 50,00", body)
        self.assertIn("R$ 10,00", body.split("Total")[-1])
        e = self.client.get(self.export)
        text = e.content.decode("utf-8-sig")
        self.assertIn("10.00", text)
        self.assertNotIn("50.00", text)

    def test_empty_five_zeros_and_message(self):
        r = self.client.get(self.report)
        self.assertEqual(r.status_code, 200)
        body = r.content.decode()
        for label in ["Novo", "Qualificado", "Proposta", "Ganho", "Perdido", "Total"]:
            self.assertIn(label, body)
        self.assertIn('id="pipeline-empty"', body)
        self.assertIn('role="status"', body)
        self.assertIn("Não há oportunidades para a seleção atual.", body)
        self.assertIn("R$ 0,00", body)
        p = TableCounter()
        p.feed(body)
        self.assertEqual(p.row_th, 6)
        self.assertEqual(p.col_th, 3)
        self.assertIn("Pipeline por previsão de fechamento", body)

    def test_exact_sums_no_filter_includes_null(self):
        self._mk(self.owner, "new", "5.00", None)
        self._mk(self.owner, "qualified", "7.00", None)
        self._mk(self.owner, "proposal", "9.00", None)
        self._mk(self.owner, "won", "100.00", None)
        self._mk(self.owner, "won", "100.00", None)
        self._mk(self.owner, "lost", "100.00", None)
        r = self.client.get(self.report)
        body = r.content.decode()
        self.assertIn("R$ 5,00", body)
        self.assertIn("R$ 7,00", body)
        self.assertIn("R$ 9,00", body)
        self.assertIn("R$ 200,00", body)
        self.assertIn("R$ 100,00", body)
        self.assertIn("R$ 321,00", body)
        self.assertNotIn('id="pipeline-empty"', body)
        e = self.client.get(self.export)
        text = e.content.decode("utf-8-sig")
        rows = list(csv.reader(io.StringIO(text)))
        self.assertEqual(rows[0], ["Etapa", "Oportunidades", "Valor (R$)"])
        self.assertEqual(rows[1], ["Novo", "1", "5.00"])
        self.assertEqual(rows[2], ["Qualificado", "1", "7.00"])
        self.assertEqual(rows[3], ["Proposta", "1", "9.00"])
        self.assertEqual(rows[4], ["Ganho", "2", "200.00"])
        self.assertEqual(rows[5], ["Perdido", "1", "100.00"])
        self.assertEqual(rows[6], ["Total", "6", "321.00"])

    def test_inclusive_filters_and_null(self):
        self._mk(self.owner, "new", "100.00", "2024-01-09")
        self._mk(self.owner, "qualified", "5.00", "2024-01-10")
        self._mk(self.owner, "proposal", "7.00", "2024-01-11")
        self._mk(self.owner, "won", "9.00", None)
        r_all = self.client.get(self.report)
        self.assertIn("R$ 121,00", r_all.content.decode())
        r_end = self.client.get(self.report + "?end=2024-01-10")
        body = r_end.content.decode()
        self.assertIn("R$ 105,00", body)
        self.assertNotIn('id="pipeline-empty"', body)
        r_one = self.client.get(self.report + "?start=2024-01-10&end=2024-01-10")
        self.assertIn("R$ 5,00", r_one.content.decode())
        self.assertIn(">1<", r_one.content.decode())
        r_start = self.client.get(self.report + "?start=2024-01-10")
        self.assertIn("R$ 12,00", r_start.content.decode())
        e_end = self.client.get(self.export + "?end=2024-01-10")
        text = e_end.content.decode("utf-8-sig")
        rows = list(csv.reader(io.StringIO(text)))
        self.assertEqual(rows[-1], ["Total", "2", "105.00"])
        r_f = self.client.get(self.report + "?start=2024-01-01")
        self.assertNotIn("R$ 121,00", r_f.content.decode())

    def test_invalid_html_and_export(self):
        bad = [
            "?foo=bar", "?start=2024-01-01&start=2024-01-01",
            "?start=2024-01-01&start=2024-01-02", "?end=2024-01-01&end=2024-01-01",
            "?start=20240101", "?start=2024-1-01", "?start=2024-02-30",
            "?start=0000-01-01", "?start=2024-01-10&end=2024-01-01",
            "?START=2024-01-01", "?start=2024-13-01",
        ]
        for q in bad:
            r = self.client.get(self.report + q)
            self.assertEqual(r.status_code, 400, q)
            body = r.content.decode()
            self.assertIn('role="alert"', body)
            self.assertIn("Filtros inválidos. Use datas em AAAA-MM-DD, sem repetir parâmetros, com início menor ou igual ao fim.", body)
            self.assertNotIn("<table", body)
            self.assertNotIn("Exportar CSV", body)
            self.assertNotIn("Total", body)
            e = self.client.get(self.export + q)
            self.assertEqual(e.status_code, 400, q)
            self.assertTrue(e["Content-Type"].startswith("text/plain"))
            self.assertNotIn("Content-Disposition", e)
            self.assertFalse(e.content.startswith(b"\xef\xbb\xbf"))
            self.assertNotIn(b"Etapa,Oportunidades", e.content)
        dup_space = self.client.get(self.report + "?start=2024-01-01%20")
        self.assertEqual(dup_space.status_code, 400)
        for q in ["", "?start=&end=", "?start=2024-01-01", "?end=2024-01-10", "?start=2024-01-01&end=2024-01-31"]:
            self.assertEqual(self.client.get(self.report + q).status_code, 200, q)
            self.assertEqual(self.client.get(self.export + q).status_code, 200, q)

    def test_csv_format_and_links(self):
        self._mk(self.owner, "new", "5.00", "2024-01-10")
        r = self.client.get(self.report + "?start=2024-01-01&end=2024-01-31")
        body = r.content.decode()
        self.assertIn('action="/reports/pipeline/"', body)
        self.assertIn('<label for="id-start">De</label>', body)
        self.assertIn("Até", body)
        self.assertIn('type="date"', body)
        self.assertIn(">Filtrar<", body)
        self.assertIn("Limpar filtros", body)
        self.assertIn("Voltar para oportunidades", body)
        self.assertIn("Exportar CSV", body)
        self.assertIn("start=2024-01-01", body)
        self.assertIn("end=2024-01-31", body)
        self.assertNotIn("T new", body)
        e = self.client.get(self.export + "?start=2024-01-01&end=2024-01-31")
        self.assertEqual(e.status_code, 200)
        self.assertTrue(e["Content-Type"].startswith("text/csv"))
        self.assertIn("charset=utf-8", e["Content-Type"])
        self.assertEqual(e["Content-Disposition"], 'attachment; filename="gemcrm-pipeline.csv"')
        self.assertTrue(e.content.startswith(b"\xef\xbb\xbf"))
        self.assertIn(b"\r\n", e.content)
        text = e.content.decode("utf-8-sig")
        self.assertTrue(text.splitlines()[0].startswith("Etapa,Oportunidades"))

    @override_settings(USE_THOUSAND_SEPARATOR=True)
    def test_large_exact_no_grouping(self):
        self._mk(self.owner, "won", "999999999999.99", "2024-03-01")
        self._mk(self.owner, "won", "999999999999.99", "2024-03-01")
        r = self.client.get(self.report)
        body = r.content.decode()
        self.assertIn("R$ 1999999999999,98", body)
        self.assertNotIn("1.999", body)
        e = self.client.get(self.export)
        text = e.content.decode("utf-8-sig")
        self.assertIn("1999999999999.98", text)
