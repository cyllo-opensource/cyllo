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
from odoo.tests import tagged

from .common import WhatsappAutomationCommon


@tagged('post_install', '-at_install')
class TestSaleOrder(WhatsappAutomationCommon):
    """Tests for the WhatsApp additions to `sale.order`."""

    def setUp(self):
        super().setUp()
        self.order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [(0, 0, {'product_id': self.product.id,
                                   'product_uom_qty': 2})],
        })

    def test_defaults(self):
        self.assertFalse(self.order.whatsapp_order)
        self.assertFalse(self.order.template_id)
        self.assertFalse(self.order.flow_id)

    def test_fields_are_not_copied(self):
        self.order.write({'whatsapp_order': True,
                          'template_id': self._create_template().id,
                          'flow_id': self._create_flow().id})
        copy = self.order.copy()
        self.assertFalse(copy.whatsapp_order)
        self.assertFalse(copy.template_id)
        self.assertFalse(copy.flow_id)

    def test_view_template_action(self):
        template = self._create_template()
        self.order.template_id = template
        action = self.order.action_view_wa_template()
        self.assertEqual(action['res_model'], 'whatsapp.template')
        self.assertEqual(action['res_id'], template.id)

    def test_send_by_whatsapp_action(self):
        template = self._create_template(state='approved')
        self.order.template_id = template
        action = self.order.action_send_by_whatsapp()
        self.assertEqual(action['res_model'], 'whatsapp.template.message')
        self.assertEqual(action['target'], 'new')
        ctx = action['context']
        self.assertEqual(ctx['default_wa_template_id'], template.id)
        self.assertEqual(ctx['default_res_id'], self.order.id)
        self.assertEqual(ctx['default_model_id'],
                         self.env['ir.model']._get('sale.order').id)
