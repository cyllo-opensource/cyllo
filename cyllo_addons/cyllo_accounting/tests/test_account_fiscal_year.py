# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cyllo(<https://www.cyllo.com>)
#    Author: Cyllo(<https://www.cyllo.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError
from datetime import date, timedelta


class TestAccountFiscalYear(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestAccountFiscalYear, cls).setUpClass()
        cls.company = cls.env['res.company'].create({'name': 'Test Fiscal Year Company'})
        cls.FiscalYear = cls.env['account.fiscal.year']

        cls.fiscal_year = cls.FiscalYear.create({
            'name': 'Test Fiscal Year Today',
            'start_date': date.today(),
            'end_date': date.today() + timedelta(days=365),
            'company_id': cls.company.id,
        })

    def test_check_start_date_valid(self):
        """Test valid start and end dates."""
        self.assertEqual(self.fiscal_year.start_date, date.today())

    def test_check_start_date_invalid(self):
        """Test ending date prior to starting date."""
        with self.assertRaises(UserError):
            self.FiscalYear.create({
                'name': 'Invalid Year',
                'start_date': date.today() + timedelta(days=365),
                'end_date': date.today(),
                'company_id': self.company.id,
            })

    def test_check_start_date_overlap(self):
        """Test overlapping fiscal years."""
        with self.assertRaises(UserError):
            self.FiscalYear.create({
                'name': 'Overlap Year',
                'start_date': date.today() + timedelta(days=10),
                'end_date': date.today() + timedelta(days=200),
                'company_id': self.company.id,
            })

    def test_action_draft(self):
        self.fiscal_year.action_draft()
        self.assertEqual(self.fiscal_year.state, 'draft')

    def test_action_open(self):
        self.fiscal_year.action_open()
        self.assertEqual(self.fiscal_year.state, 'open')

    def test_action_reopen(self):
        self.fiscal_year.state = 'close'
        self.fiscal_year.action_reopen()
        self.assertEqual(self.fiscal_year.state, 'open')

    def test_action_close(self):
        result = self.fiscal_year.action_close()
        self.assertEqual(result.get('type'), 'ir.actions.act_window')
        self.assertEqual(result.get('res_model'), 'account.move.lock')

    def test_unlink_open(self):
        """Test unlink when state is open."""
        self.fiscal_year.action_open()
        with self.assertRaises(UserError):
            self.fiscal_year.unlink()

    def test_unlink_draft(self):
        """Test unlink when state is draft."""
        self.fiscal_year.action_draft()
        self.fiscal_year.unlink()
        self.assertFalse(self.FiscalYear.search([('id', '=', self.fiscal_year.id)]))
