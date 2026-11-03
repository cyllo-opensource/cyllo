# -*- coding: utf-8 -*-
from datetime import date, timedelta

from dateutil.relativedelta import relativedelta
from odoo import fields
from odoo.tests.common import TransactionCase


class TestGeneralLedgerAccountSelection(TransactionCase):
    """Regression coverage for General Ledger account inclusion."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.report = cls.env['report.cyllo_accounting.general_ledger']
        cls.journal = cls.env['account.journal'].search([
            ('company_id', '=', cls.company.id), ('type', '=', 'general'),
        ], limit=1)
        if not cls.journal:
            cls.journal = cls.env['account.journal'].create({
                'name': 'GL Selection', 'code': 'GLSEL', 'type': 'general',
                'company_id': cls.company.id,
            })
        cls.offset_account = cls.env['account.account'].create({
            'name': 'GL selection offset', 'code': 'GLSEL999',
            'account_type': 'equity', 'company_id': cls.company.id,
        })

    @classmethod
    def _account(cls, code):
        return cls.env['account.account'].create({
            'name': 'GL selection %s' % code, 'code': code,
            'account_type': 'asset_current', 'company_id': cls.company.id,
        })

    @classmethod
    def _post_move(cls, date, account, debit=0.0, credit=0.0):
        move = cls.env['account.move'].create({
            'move_type': 'entry', 'date': date, 'journal_id': cls.journal.id,
            'line_ids': [
                fields.Command.create({
                    'account_id': account.id, 'debit': debit, 'credit': credit,
                }),
                fields.Command.create({
                    'account_id': cls.offset_account.id,
                    'debit': credit, 'credit': debit,
                }),
            ],
        })
        move.action_post()

    def _report_account_sums(self):
        start_date = date.today().replace(day=1)
        end_date = start_date + relativedelta(months=1) - timedelta(days=1)
        _data, sums, _pages, _filters, _currency = self.report.get_report(
            start_date=start_date, end_date=end_date,
            company_ids=[self.company.id], target_move=['posted'],
        )
        return {
            values[0]['account_id']: values[0]
            for values in sums[0].values()
        }

    def test_accounts_with_opening_or_zero_net_period_activity_are_kept(self):
        start_date = date.today().replace(day=1)
        end_date = start_date + relativedelta(months=1) - timedelta(days=1)
        opening_only = self._account('GLSEL001')
        debit_only = self._account('GLSEL002')
        credit_only = self._account('GLSEL003')
        zero_net = self._account('GLSEL004')
        future_only = self._account('GLSEL005')

        self._post_move(start_date - timedelta(days=1), opening_only, debit=100.0)
        self._post_move(start_date + timedelta(days=4), debit_only, debit=25.0)
        self._post_move(start_date + timedelta(days=5), credit_only, credit=30.0)
        self._post_move(start_date + timedelta(days=6), zero_net, debit=40.0)
        self._post_move(start_date + timedelta(days=7), zero_net, credit=40.0)
        self._post_move(end_date + timedelta(days=1), future_only, debit=50.0)

        account_sums = self._report_account_sums()

        self.assertIn(opening_only.id, account_sums)
        self.assertEqual(account_sums[opening_only.id]['opening_debit'], 100.0)
        self.assertEqual(account_sums[opening_only.id]['total_debit'], 100.0)
        self.assertIn(debit_only.id, account_sums)
        self.assertIn(credit_only.id, account_sums)
        self.assertIn(zero_net.id, account_sums)
        self.assertEqual(account_sums[zero_net.id]['total_debit'], 40.0)
        self.assertEqual(account_sums[zero_net.id]['total_credit'], 40.0)
        self.assertNotIn(future_only.id, account_sums)
