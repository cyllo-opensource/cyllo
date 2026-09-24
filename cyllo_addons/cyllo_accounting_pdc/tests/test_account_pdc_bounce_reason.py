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


class TestAccountPdcBounceReason(TestCylloAccountingPdc):

    def test_action_bounce(self):
        bounce_reason = self.env['account.pdc.bounce.reason'].create({
            'reason': 'No Balance',
            'bank_name': 'ABC',
            'cheque_reference': 'Test Ref',
            'pdc_payment_id': self.pdc_payment.id
        })
        self.pdc_payment.action_post()
        bounce_reason.action_bounce()
        self.assertEqual(bounce_reason.pdc_payment_id.payment_status,
                         'bounced')
