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
from odoo.addons.cyllo_accounting_pdc.tests.common import TestCylloAccountingPdc


class TesAccountJournal(TestCylloAccountingPdc):

    def test_default_outbound_payment_methods(self):
        self.assertTrue(
            self.account_journal._default_outbound_payment_methods().mapped(
                'name').index('PDC'))

    def test_default_inbound_payment_methods(self):
        self.assertTrue(
            self.account_journal._default_inbound_payment_methods().mapped(
                'name').index('PDC'))

    def test_compute_available_payment_method_ids(self):
        self.assertTrue(
            self.account_journal.available_payment_method_ids.mapped(
                'name').index('PDC'))
