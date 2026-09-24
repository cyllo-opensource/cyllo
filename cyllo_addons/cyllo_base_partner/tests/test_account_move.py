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
from odoo.tests import TransactionCase


class TestAccountMove(TransactionCase):
    """
    Test suite for the `account.move` model focusing on the `_onchange_partner_id` method.

    This suite verifies that the partner list (`partner_ids`) is updated correctly
    based on the `move_type` when the `partner_id` is changed. It checks behavior for:
      - Customer invoices
      - Customer credit notes
      - Vendor bills
      - Vendor credit notes
      - Journal entries / Other moves
    """

    @classmethod
    def setUpClass(cls):
        """
        Set up reusable test data for the entire test class.

        Creates:
            - A customer-only partner
            - A vendor-only partner
            - A mixed partner (both customer and vendor)
        These are used to verify partner list updates in `_onchange_partner_id`.
        """
        super().setUpClass()

        cls.customer_partner = cls.env['res.partner'].create({
            'name': 'Customer Partner',
            'is_customer': True,
            'is_vendor': False,
        })
        cls.vendor_partner = cls.env['res.partner'].create({
            'name': 'Vendor Partner',
            'is_customer': False,
            'is_vendor': True,
        })
        cls.mixed_partner = cls.env['res.partner'].create({
            'name': 'Mixed Partner',
            'is_customer': True,
            'is_vendor': True,
        })

    def test_onchange_partner_id(self):
        """
        Test `_onchange_partner_id` behavior for different move types.

        For each move type:
            - Creates a new `account.move` record with the given partner and move type.
            - Calls `_onchange_partner_id` to update `partner_ids`.
            - Asserts that the correct partner IDs appear in `partner_ids` based on the logic:
                * Customer invoices / credit notes: should contain customer and mixed partners only.
                * Vendor bills / credit notes: should contain vendor and mixed partners only.
                * Journal entries / other: should contain all partners.
        """

        test_cases = [
            ('out_invoice', self.customer_partner.id, "Customer Invoice"),
            ('out_refund', self.customer_partner.id, "Customer Credit Note"),
            ('in_invoice', self.vendor_partner.id, "Vendor Bill"),
            ('in_refund', self.vendor_partner.id, "Vendor Credit Note"),
            ('entry', self.customer_partner.id, "Journal Entry / Other"),
        ]

        for move_type, partner_id, description in test_cases:
            move = self.env['account.move'].new({
                'move_type': move_type,
                'partner_id': partner_id
            })
            move._onchange_partner_id()

            if move_type in ('out_invoice', 'out_refund'):
                self.assertIn(self.customer_partner.id, move.partner_ids.ids)
                self.assertIn(self.mixed_partner.id, move.partner_ids.ids)
                self.assertNotIn(self.vendor_partner.id, move.partner_ids.ids)

            elif move_type in ('in_invoice', 'in_refund'):
                self.assertIn(self.vendor_partner.id, move.partner_ids.ids)
                self.assertIn(self.mixed_partner.id, move.partner_ids.ids)
                self.assertNotIn(self.customer_partner.id, move.partner_ids.ids)

            else:
                self.assertIn(self.customer_partner.id, move.partner_ids.ids)
                self.assertIn(self.vendor_partner.id, move.partner_ids.ids)
                self.assertIn(self.mixed_partner.id, move.partner_ids.ids)
