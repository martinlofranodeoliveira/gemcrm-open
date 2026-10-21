import copy
import unittest
from crm.features.pipeline_board_snapshot import run_feature


class PipelineBoardSnapshotTest(unittest.TestCase):
    def test_empty_payload_defaults(self):
        out = run_feature({})
        self.assertEqual(out["deal_count"], 0)
        self.assertEqual(out["grand"], {"count": 0, "total_cents": 0, "total_csv": "0.00", "total_display": "R$ 0,00"})
        for key in ("new", "qualified", "proposal", "won", "lost"):
            self.assertEqual(out["columns"][key]["count"], 0)
            self.assertEqual(out["columns"][key]["deals"], [])
            self.assertEqual(out["columns"][key]["total_csv"], "0.00")
            self.assertEqual(out["columns"][key]["total_display"], "R$ 0,00")

    def test_documented_two_deal_example(self):
        payload = {"deals": [{"pk": 1, "stage": "new", "title": "Padaria", "value": "100.00"}, {"pk": 2, "stage": "won", "title": "Mercado", "value": "234.50"}]}
        out = run_feature(payload)
        self.assertEqual(out["deal_count"], 2)
        self.assertEqual(out["columns"]["new"]["label"], "Novo")
        self.assertEqual(out["columns"]["new"]["deals"][0], {"pk": 1, "stage": "new", "title": "Padaria", "value_cents": 10000, "value_csv": "100.00", "value_display": "R$ 100,00"})
        self.assertEqual(out["columns"]["won"]["deals"][0]["value_cents"], 23450)
        self.assertEqual(out["grand"], {"count": 2, "total_cents": 33450, "total_csv": "334.50", "total_display": "R$ 334,50"})

    def test_value_variants_and_totals(self):
        payload = {"deals": [{"pk": 10, "stage": "proposal", "title": "B", "value": "100", "company": "Extra"}, {"pk": 9, "stage": "proposal", "title": "A", "value": "100.5"}, {"pk": 11, "stage": "proposal", "title": "C", "value": "100.05"}]}
        out = run_feature(payload)
        deals = out["columns"]["proposal"]["deals"]
        self.assertEqual([d["pk"] for d in deals], [10, 9, 11])
        self.assertEqual([d["value_cents"] for d in deals], [10000, 10050, 10005])
        self.assertEqual([d["value_csv"] for d in deals], ["100.00", "100.50", "100.05"])
        self.assertEqual([d["value_display"] for d in deals], ["R$ 100,00", "R$ 100,50", "R$ 100,05"])
        self.assertEqual(out["columns"]["proposal"]["total_cents"], 30055)
        self.assertEqual(out["columns"]["proposal"]["total_csv"], "300.55")
        self.assertEqual(out["grand"]["total_display"], "R$ 300,55")

    def test_labels_and_order(self):
        payload = {"deals": [{"pk": 1, "title": "A", "stage": "lost", "value": "1.00"}, {"pk": 2, "title": "B", "stage": "new", "value": "2.00"}, {"pk": 3, "title": "C", "stage": "qualified", "value": "3.00"}, {"pk": 4, "title": "D", "stage": "proposal", "value": "4.00"}, {"pk": 5, "title": "E", "stage": "won", "value": "5.00"}, {"pk": 6, "title": "F", "stage": "new", "value": "6.00"}]}
        out = run_feature(payload)
        self.assertEqual(out["columns"]["new"]["label"], "Novo")
        self.assertEqual(out["columns"]["qualified"]["label"], "Qualificado")
        self.assertEqual(out["columns"]["proposal"]["label"], "Proposta")
        self.assertEqual(out["columns"]["won"]["label"], "Ganho")
        self.assertEqual(out["columns"]["lost"]["label"], "Perdido")
        self.assertEqual([d["pk"] for d in out["columns"]["new"]["deals"]], [2, 6])
        self.assertEqual(out["deal_count"], 6)
        self.assertEqual(out["grand"]["count"], 6)
        self.assertEqual(list(out["columns"].keys()), ["new", "qualified", "proposal", "won", "lost"])

    def test_extra_keys_ignored_and_no_mutation(self):
        payload = {"deals": [{"pk": 1, "title": "T", "stage": "new", "value": "10.00", "extra": 1}], "other": 99}
        snapshot = copy.deepcopy(payload)
        out = run_feature(payload)
        self.assertEqual(payload, snapshot)
        self.assertEqual(set(out["columns"]["new"]["deals"][0].keys()), {"pk", "title", "stage", "value_cents", "value_csv", "value_display"})
        self.assertEqual(set(out.keys()), {"deal_count", "columns", "grand"})
        again = run_feature(payload)
        self.assertEqual(out, again)

    def test_rejects_bad_payload_shapes(self):
        for bad in (None, [], "x", 5, True):
            with self.assertRaises(ValueError):
                run_feature(bad)
        for bad_deals in (None, {}, "x", 5):
            with self.assertRaises(ValueError):
                run_feature({"deals": bad_deals})
        with self.assertRaises(ValueError):
            run_feature({"deals": [{"pk": 1, "title": "T", "stage": "new", "value": "1.00"}] * 2001})

    def test_rejects_malformed_deals(self):
        good = {"pk": 1, "title": "Ok", "stage": "new", "value": "1.00"}
        bads = [
            {"pk": True, "title": "Ok", "stage": "new", "value": "1.00"},
            {"pk": 0, "title": "Ok", "stage": "new", "value": "1.00"},
            {"pk": "1", "title": "Ok", "stage": "new", "value": "1.00"},
            {"pk": 9007199254740992, "title": "Ok", "stage": "new", "value": "1.00"},
            {"pk": 1, "title": "", "stage": "new", "value": "1.00"},
            {"pk": 1, "title": "x" * 181, "stage": "new", "value": "1.00"},
            {"pk": 1, "title": "Ok", "stage": "bad", "value": "1.00"},
            {"pk": 1, "title": "Ok", "stage": "new", "value": "01.00"},
            {"pk": 1, "title": "Ok", "stage": "new", "value": "1.000"},
            {"pk": 1, "title": "Ok", "stage": "new", "value": ""},
            {"pk": 1, "title": "Ok", "stage": "new", "value": 5},
            {"pk": 1, "title": "Ok", "stage": "new", "value": "99999999999999.00"},
            {"pk": 1, "title": "Ok", "stage": "new"},
            "not-a-dict",
        ]
        for bad in bads:
            with self.assertRaises(ValueError):
                run_feature({"deals": [bad]})
        out = run_feature({"deals": [good]})
        self.assertEqual(out["deal_count"], 1)

    def test_zero_formatting(self):
        out = run_feature({"deals": [{"pk": 1, "title": "Z", "stage": "lost", "value": "0"}]})
        deal = out["columns"]["lost"]["deals"][0]
        self.assertEqual(deal["value_cents"], 0)
        self.assertEqual(deal["value_csv"], "0.00")
        self.assertEqual(deal["value_display"], "R$ 0,00")


if __name__ == "__main__":
    unittest.main()
