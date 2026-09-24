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


class TestAccountAccount(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestAccountAccount, cls).setUpClass()
        cls.Account = cls.env['account.account']
        cls.account = cls.Account.create({
            'name': 'Test Account',
            'code': '999998.TEST.ACC',
            'account_type': 'asset_current',
        })

    def test_account_creation(self):
        """Test the creation of an account.account record."""
        self.assertEqual(self.account.name, 'Test Account')
        self.assertTrue(self.account.id)

    def test_annotation_mixin_inherited(self):
        """Test that account.account inherits annotation.mixin."""
        self.assertTrue(hasattr(self.account, 'annotations'))

    def test_move_line_ids_field_exists(self):
        """Test that the move_line_ids One2many field exists."""
        self.assertTrue('move_line_ids' in self.account._fields)

    def test_write_annotations_on_account(self):
        """Test writing annotations through the mixin on account."""
        self.account.write_annotations('1', 'General Ledger Note')
        self.assertEqual(self.account.annotations.get('1'), 'General Ledger Note')

    def test_remove_annotations_on_account(self):
        """Test removing annotations through the mixin on account."""
        self.account.write_annotations('2', 'Partner Ledger Note')
        self.account.remove_annotations('2')
        self.assertNotIn('2', self.account.annotations or {})

    def test_move_line_ids_relationship(self):
        """Test move_line_ids is properly linked to account.move.line."""
        journal = self.env['account.journal'].search([('type', '=', 'general')], limit=1)
        if journal:
            move = self.env['account.move'].create({
                'journal_id': journal.id,
                'line_ids': [(0, 0, {
                    'account_id': self.account.id,
                    'name': 'Test Line',
                    'debit': 100,
                }), (0, 0, {
                    'account_id': self.account.id,
                    'name': 'Test Line 2',
                    'credit': 100,
                })],
            })
            self.assertTrue(self.account.move_line_ids)
