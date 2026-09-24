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
import logging
from odoo.addons.cyllo_subscription.tests.common import TestCylloSubscription

_logger = logging.getLogger(__name__)


class TestAccountMove(TestCylloSubscription):

    def test_ir_cron_action_post(self):
        _logger.info("Starts test_ir_cron_action_post")
        self.sale_order_template.invoice_creation = 'sent'
        self.account_move.ir_cron_action_post()
        mail = self.env.ref('cyllo_subscription.mail_template_invoice_for_subscription')
        self.assertEqual(mail['email_to'], self.partner.email, "An email should be sent to the partner for 'sent' invoice creation.")
        _logger.info("Ends test_ir_cron_action_post")
