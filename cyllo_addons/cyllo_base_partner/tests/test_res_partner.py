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


class TestResPartner(TransactionCase):
    """Test suite for verifying the `is_customer` and `is_vendor` flags
    in the res.partner model when creating partners with various rank combinations.
    """

    @classmethod
    def setUpClass(cls):
        """Set up test data for the entire class."""
        super().setUpClass()
        cls.partner = cls.env['res.partner']

    def test_create(self):
        """Test `create` method behavior for all customer/vendor rank combinations."""
        partner = self.partner.create({
            'name': 'Test Partner',
            'customer_rank' : 1,
            'supplier_rank' : 1,
        })
        self.assertTrue(partner.is_customer)
        self.assertTrue(partner.is_vendor)
        partner = self.partner.create({
            'name': 'None',
            'customer_rank': 0,
            'supplier_rank': 0,
        })
        self.assertFalse(partner.is_customer)
        self.assertFalse(partner.is_vendor)
        partner = self.partner.create({
            'name': 'customer only',
            'customer_rank': 1,
            'supplier_rank': 0,
        })
        self.assertTrue(partner.is_customer)
        self.assertFalse(partner.is_vendor)
        partner = self.partner.create({
            'name': 'vendor only',
            'customer_rank': 0,
            'supplier_rank': 1,
        })
        self.assertFalse(partner.is_customer)
        self.assertTrue(partner.is_vendor)
