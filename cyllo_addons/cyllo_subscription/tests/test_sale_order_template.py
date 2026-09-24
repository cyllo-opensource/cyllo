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
from odoo import _
from odoo.addons.cyllo_subscription.tests.common import TestCylloSubscription

_logger = logging.getLogger(__name__)

class TestSaleOrderTemplate(TestCylloSubscription):

    def test_action_order(self):
        _logger.info("Starts test_action_subscriptions")
        orders = self.env['sale.order'].search([('sale_order_template_id', '=', self.sale_order_template.id)])
        self.assertEqual(self.sale_order5.action_order(), {
            'type': 'ir.actions.act_window',
            'name': _('Sale Order'),
            'res_model': 'sale.order',
            'view_mode': 'tree,form',
            'target': 'current',
            'domain': [('id', 'in', orders.ids)]
        },
        "Error in test_action_subscriptions")
        _logger.info("Ends test_action_subscriptions")
