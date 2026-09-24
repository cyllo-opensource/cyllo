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
from odoo.addons.cyllo_advance_payment.tests.common import \
    TestCylloAdvancePayment


class TestPurchase(TestCylloAdvancePayment):
    def test_compute_total_advance_amount(self):
        self.assertEqual(self.purchase1.total_advance_amount,
                         (self.payment.amount + self.payment2.amount))

    def test_action_advance_payment(self):
        payment = self.purchase1.action_advance_payment()
        self.assertEqual(payment['name'], 'Advance Payment')
        self.assertEqual(payment['view_type'], 'form')
        self.assertEqual(payment['view_mode'], 'form')
        self.assertEqual(payment['target'], 'new')
