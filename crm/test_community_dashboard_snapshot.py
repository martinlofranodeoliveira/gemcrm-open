import copy
import unittest
from crm.features.dashboard_snapshot import run_feature


class DashboardSnapshotTest(unittest.TestCase):
    def test_first_example(self):
        payload = {'today': '2026-03-10', 'deals': [{'pk': 1, 'stage': 'new', 'value': '100.00'}, {'pk': 2, 'stage': 'won', 'value': '234.50'}], 'tasks': [{'pk': 1, 'due_date': '2026-03-09', 'completed': False}, {'pk': 2, 'due_date': '2026-03-10', 'completed': False}, {'pk': 3, 'due_date': '2026-03-11', 'completed': False}, {'pk': 4, 'due_date': '2026-03-09', 'completed': True}]}
        result = run_feature(payload)
        self.assertEqual(result['today'], '2026-03-10')
        self.assertEqual(result['deals_open_count'], 1)
        self.assertEqual(result['deals_closed_count'], 1)
        self.assertEqual(result['deals_open_total_cents'], 10000)
        self.assertEqual(result['deals_open_total_csv'], '100.00')
        self.assertEqual(result['deals_open_total_display'], 'R$ 100,00')
        self.assertEqual(result['tasks_open_count'], 3)
        self.assertEqual(result['tasks_completed_count'], 1)
        self.assertEqual(result['tasks_overdue_count'], 1)
        self.assertEqual(result['tasks_due_today_count'], 1)
        self.assertEqual(result['tasks_upcoming_count'], 1)
        self.assertEqual(result['tasks_due_count'], 2)

    def test_empty_leap_day(self):
        result = run_feature({'today': '2024-02-29', 'deals': [], 'tasks': []})
        self.assertEqual(result['today'], '2024-02-29')
        self.assertEqual(result['deals_open_count'], 0)
        self.assertEqual(result['deals_closed_count'], 0)
        self.assertEqual(result['deals_open_total_cents'], 0)
        self.assertEqual(result['deals_open_total_csv'], '0.00')
        self.assertEqual(result['deals_open_total_display'], 'R$ 0,00')
        self.assertEqual(result['tasks_open_count'], 0)
        self.assertEqual(result['tasks_completed_count'], 0)
        self.assertEqual(result['tasks_overdue_count'], 0)
        self.assertEqual(result['tasks_due_today_count'], 0)
        self.assertEqual(result['tasks_upcoming_count'], 0)
        self.assertEqual(result['tasks_due_count'], 0)

    def test_cents_conversion(self):
        payload = {'today': '2026-01-15', 'deals': [{'pk': 10, 'stage': 'qualified', 'value': '100.5'}, {'pk': 11, 'stage': 'proposal', 'value': '1134.05'}], 'tasks': [{'pk': 5, 'due_date': '2026-01-15', 'completed': False}]}
        result = run_feature(payload)
        self.assertEqual(result['deals_open_count'], 2)
        self.assertEqual(result['deals_closed_count'], 0)
        self.assertEqual(result['deals_open_total_cents'], 123455)
        self.assertEqual(result['deals_open_total_csv'], '1234.55')
        self.assertEqual(result['deals_open_total_display'], 'R$ 1234,55')
        self.assertEqual(result['tasks_due_count'], 1)

    def test_open_closed_stages(self):
        payload = {'today': '2026-05-01', 'deals': [{'pk': 1, 'stage': 'new', 'value': '100'}, {'pk': 2, 'stage': 'qualified', 'value': '100.05'}, {'pk': 3, 'stage': 'proposal', 'value': '10.10'}, {'pk': 4, 'stage': 'won', 'value': '999.99'}, {'pk': 5, 'stage': 'lost', 'value': '1.00'}], 'tasks': []}
        result = run_feature(payload)
        self.assertEqual(result['deals_open_count'], 3)
        self.assertEqual(result['deals_closed_count'], 2)
        self.assertEqual(result['deals_open_total_cents'], 10000 + 10005 + 1010)
        self.assertEqual(result['deals_open_total_csv'], '210.15')
        self.assertEqual(result['deals_open_total_display'], 'R$ 210,15')

    def test_task_split_and_completed_never_overdue(self):
        payload = {'today': '2026-03-10', 'deals': [], 'tasks': [{'pk': 1, 'due_date': '2026-03-01', 'completed': False}, {'pk': 2, 'due_date': '2026-03-10', 'completed': False}, {'pk': 3, 'due_date': '2026-03-20', 'completed': False}, {'pk': 4, 'due_date': '2026-03-01', 'completed': True}]}
        result = run_feature(payload)
        self.assertEqual(result['tasks_open_count'], 3)
        self.assertEqual(result['tasks_completed_count'], 1)
        self.assertEqual(result['tasks_overdue_count'], 1)
        self.assertEqual(result['tasks_due_today_count'], 1)
        self.assertEqual(result['tasks_upcoming_count'], 1)
        self.assertEqual(result['tasks_due_count'], 2)

    def test_missing_optional_defaults(self):
        result = run_feature({'today': '2026-01-01'})
        self.assertEqual(result['deals_open_total_csv'], '0.00')
        self.assertEqual(result['deals_open_total_display'], 'R$ 0,00')
        self.assertEqual(result['tasks_due_count'], 0)

    def test_invalid_today(self):
        for bad in ['2023-02-29', '2026-13-01', '2026-00-10', '2026-02-30', 'not-a-date', '2026/03/10', '2026-3-1', '']:
            with self.assertRaises(ValueError):
                run_feature({'today': bad})
        with self.assertRaises(ValueError):
            run_feature({})
        with self.assertRaises(ValueError):
            run_feature({'today': None})

    def test_invalid_value(self):
        bad_values = ['00.10', '01', '1.000', '1.', '.5', '', ' 10', '+10', '-5', '1,00', '9999999999999.99', '1000000000000.00']
        for v in bad_values:
            with self.assertRaises(ValueError):
                run_feature({'today': '2026-01-01', 'deals': [{'pk': 1, 'stage': 'new', 'value': v}]})
        with self.assertRaises(ValueError):
            run_feature({'today': '2026-01-01', 'deals': [{'pk': 1, 'stage': 'new', 'value': 100}]})

    def test_invalid_stage_pk_completed_due(self):
        with self.assertRaises(ValueError):
            run_feature({'today': '2026-01-01', 'deals': [{'pk': 1, 'stage': 'open', 'value': '10.00'}]})
        with self.assertRaises(ValueError):
            run_feature({'today': '2026-01-01', 'deals': [{'pk': True, 'stage': 'new', 'value': '10.00'}]})
        with self.assertRaises(ValueError):
            run_feature({'today': '2026-01-01', 'deals': [{'pk': 0, 'stage': 'new', 'value': '10.00'}]})
        with self.assertRaises(ValueError):
            run_feature({'today': '2026-01-01', 'deals': [{'pk': 9007199254740992, 'stage': 'new', 'value': '10.00'}]})
        with self.assertRaises(ValueError):
            run_feature({'today': '2026-01-01', 'tasks': [{'pk': 1, 'due_date': '2023-02-29', 'completed': False}]})
        with self.assertRaises(ValueError):
            run_feature({'today': '2026-01-01', 'tasks': [{'pk': 1, 'due_date': '2026-01-01', 'completed': 0}]})
        with self.assertRaises(ValueError):
            run_feature({'today': '2026-01-01', 'tasks': [{'pk': 1, 'due_date': '2026-01-01', 'completed': 1}]})
        with self.assertRaises(ValueError):
            run_feature({'today': '2026-01-01', 'tasks': [{'pk': True, 'due_date': '2026-01-01', 'completed': False}]})

    def test_invalid_envelope_and_limits(self):
        with self.assertRaises(ValueError):
            run_feature([])
        with self.assertRaises(ValueError):
            run_feature(None)
        with self.assertRaises(ValueError):
            run_feature({'today': '2026-01-01', 'deals': {}})
        with self.assertRaises(ValueError):
            run_feature({'today': '2026-01-01', 'tasks': 'x'})
        with self.assertRaises(ValueError):
            run_feature({'today': '2026-01-01', 'deals': [{'pk': 1}]})
        big_deal = {'pk': 1, 'stage': 'new', 'value': '1.00'}
        with self.assertRaises(ValueError):
            run_feature({'today': '2026-01-01', 'deals': [big_deal] * 2001})
        big_task = {'pk': 1, 'due_date': '2026-01-01', 'completed': False}
        with self.assertRaises(ValueError):
            run_feature({'today': '2026-01-01', 'tasks': [big_task] * 2001})

    def test_extra_keys_ignored_no_mutation_order(self):
        payload = {'today': '2026-03-10', 'extra': 1, 'deals': [{'pk': 2, 'stage': 'won', 'value': '5.00', 'note': 'x'}, {'pk': 1, 'stage': 'new', 'value': '10.00', 'owner': 9}], 'tasks': [{'pk': 1, 'due_date': '2026-03-09', 'completed': False, 'title': 't'}]}
        before = copy.deepcopy(payload)
        r1 = run_feature(payload)
        self.assertEqual(payload, before)
        flipped = {'today': '2026-03-10', 'deals': list(reversed(payload['deals'])), 'tasks': list(payload['tasks'])}
        r2 = run_feature(flipped)
        self.assertEqual(r1, r2)
        self.assertEqual(r1['deals_open_count'], 1)
        self.assertEqual(r1['deals_open_total_csv'], '10.00')

    def test_today_drives_comparison(self):
        tasks = [{'pk': 1, 'due_date': '2026-03-10', 'completed': False}]
        early = run_feature({'today': '2026-03-11', 'tasks': tasks})
        same = run_feature({'today': '2026-03-10', 'tasks': tasks})
        late = run_feature({'today': '2026-03-09', 'tasks': tasks})
        self.assertEqual(early['tasks_overdue_count'], 1)
        self.assertEqual(same['tasks_due_today_count'], 1)
        self.assertEqual(late['tasks_upcoming_count'], 1)

    def test_leap_and_zero_values(self):
        r = run_feature({'today': '2024-02-29', 'deals': [{'pk': 1, 'stage': 'new', 'value': '0'}, {'pk': 2, 'stage': 'new', 'value': '0.00'}], 'tasks': [{'pk': 1, 'due_date': '2024-02-29', 'completed': False}]})
        self.assertEqual(r['deals_open_total_cents'], 0)
        self.assertEqual(r['tasks_due_today_count'], 1)
        with self.assertRaises(ValueError):
            run_feature({'today': '2023-02-29'})
        with self.assertRaises(ValueError):
            run_feature({'today': '2026-01-01', 'tasks': [{'pk': 1, 'due_date': '2023-02-29', 'completed': False}]})
