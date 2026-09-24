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


class TestAccountReturn(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestAccountReturn, cls).setUpClass()
        cls.company = cls.env['res.company'].create({'name': 'Test Tax Return Company'})
        cls.Return = cls.env['account.return']
        cls.journal = cls.env['account.journal'].create({
            'name': 'Test General Journal',
            'type': 'general',
            'code': 'TSTGEN',
            'company_id': cls.company.id,
        })

        cls.tax_return = cls.Return.create({
            'name': 'Tax Return Test',
            'periodicity': 'monthly',
            'date_from': date.today(),
            'date_to': date.today(),
            'journal_id': cls.journal.id,
            'company_id': cls.company.id,
        })

    def test_model_loaded(self):
        """Test that the model is correctly loaded."""
        self.assertTrue('account.return' in self.env)

    def test_tax_return_creation(self):
        """Test creating a tax return record."""
        self.assertTrue(self.tax_return.id)
        self.assertEqual(self.tax_return.state, 'draft')
        self.assertEqual(self.tax_return.periodicity, 'monthly')

    def test_check_dates_invalid(self):
        """Test that start_date after end_date raises UserError."""
        with self.assertRaises(UserError):
            self.Return.create({
                'name': 'Invalid Date Return',
                'periodicity': 'monthly',
                'date_from': date.today() + timedelta(days=1),
                'date_to': date.today(),
                'journal_id': self.journal.id,
                'company_id': self.company.id,
            })

    def test_check_overlap(self):
        """Test that overlapping tax returns raise UserError."""
        with self.assertRaises(UserError):
            self.Return.create({
                'name': 'Overlap Return',
                'periodicity': 'monthly',
                'date_from': date.today(),
                'date_to': date.today() + timedelta(days=5),
                'journal_id': self.journal.id,
                'company_id': self.company.id,
            })

    def test_action_compute(self):
        """Test action_compute sets tax values."""
        self.tax_return.action_compute()
        # output_tax and input_tax should be computed (0 or positive)
        self.assertTrue(self.tax_return.output_tax >= 0)
        self.assertTrue(self.tax_return.input_tax >= 0)

    def test_compute_balance_amount(self):
        """Test _compute_balance_amount computation."""
        self.tax_return._compute_balance_amount()
        # balance_amount should be computed without error
        self.assertTrue(True)

    def test_action_cancel(self):
        """Test action_cancel sets state to cancelled."""
        tax_return = self.Return.create({
            'name': 'Cancel Test Return',
            'periodicity': 'monthly',
            'date_from': date.today() + timedelta(days=10),
            'date_to': date.today() + timedelta(days=20),
            'journal_id': self.journal.id,
            'company_id': self.company.id,
        })
        tax_return.action_cancel()
        self.assertEqual(tax_return.state, 'cancel')

    def test_action_draft_from_cancel(self):
        """Test action_draft resets state from cancel to draft."""
        tax_return = self.Return.create({
            'name': 'Draft Test Return',
            'periodicity': 'monthly',
            'date_from': date.today() + timedelta(days=30),
            'date_to': date.today() + timedelta(days=40),
            'journal_id': self.journal.id,
            'company_id': self.company.id,
        })
        tax_return.action_cancel()
        tax_return.action_draft()
        self.assertEqual(tax_return.state, 'draft')

    def test_unlink_draft(self):
        """Test unlink works on draft returns."""
        tax_return = self.Return.create({
            'name': 'Unlink Draft Return',
            'periodicity': 'monthly',
            'date_from': date.today() + timedelta(days=50),
            'date_to': date.today() + timedelta(days=60),
            'journal_id': self.journal.id,
            'company_id': self.company.id,
        })
        return_id = tax_return.id
        tax_return.unlink()
        self.assertFalse(self.Return.search([('id', '=', return_id)]))

    def test_action_post_not_draft(self):
        """Test action_post raises error for non-draft returns."""
        tax_return = self.Return.create({
            'name': 'Post Non-Draft Return',
            'periodicity': 'monthly',
            'date_from': date.today() + timedelta(days=70),
            'date_to': date.today() + timedelta(days=80),
            'journal_id': self.journal.id,
            'company_id': self.company.id,
        })
        tax_return.action_cancel()
        with self.assertRaises(UserError):
            tax_return.action_post()

    def test_action_open_tax_return_wizard(self):
        """Test action_open_tax_return_wizard returns wizard action."""
        result = self.tax_return.action_open_tax_return_wizard()
        self.assertEqual(result.get('res_model'), 'tax.return.wizard')
        self.assertEqual(result.get('target'), 'new')

    def test_action_validate_checks_no_checks(self):
        """Test action_validate_checks with no check_ids."""
        result = self.tax_return.action_validate_checks()
        self.assertEqual(result.get('params', {}).get('type'), 'success')
