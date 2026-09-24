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

class TestAccountTax(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestAccountTax, cls).setUpClass()
        cls.Tax = cls.env['account.tax']
        cls.tax = cls.Tax.create({
            'name': 'Test Tax',
            'amount': 10.0,
        })

    def test_tax_creation(self):
        """Test the creation of an account.tax record."""
        self.assertEqual(self.tax.name, 'Test Tax')
        self.assertTrue(self.tax.id)
