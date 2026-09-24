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
from datetime import datetime, timedelta


class TestSaleOrder(TransactionCase):
    """
    Test cases for Sale Order computed field `order_date`.
    """
    @classmethod
    def setUp(cls):
        super().setUpClass()

        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Partner',
        })

    def test_compute_order_date(self):
        """
        Test the computation of order_date from date_order.
        """
        date_order = datetime(2025,8, 25, 15, 30)
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'date_order': date_order,
        })
        self.assertEqual(sale_order.order_date, date_order.date())
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
        })
        sale_order.date_order = False
        sale_order._compute_order_date()
        self.assertFalse(sale_order.order_date)
