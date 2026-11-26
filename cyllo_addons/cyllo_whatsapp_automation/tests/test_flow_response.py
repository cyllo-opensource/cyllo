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
class TestFlowResponse(WhatsappAutomationCommon):
    """Tests for `flows.user.response` and its lead / quotation creation."""

    def setUp(self):
        super().setUp()
        self.flow = self._flow_with_content()
        self.template = self._create_template()

    def test_defaults(self):
        response = self._create_response(self.flow, self.template)
        self.assertEqual(response.state, 'draft')
        self.assertTrue(response.active)
        self.assertEqual(response.company_id, self.env.company)
        self.assertEqual(len(response.flows_user_response_line_ids), 1)

    def test_responses_deleted_with_flow(self):
        response = self._create_response(self.flow, self.template)
        self.flow.unlink()
        self.assertFalse(response.exists())

    def test_create_lead(self):
        response = self._create_response(self.flow, self.template)
        response.action_create_lead()
        self.assertEqual(response.state, 'lead_created')
        lead = self.env['crm.lead'].search(
            [('partner_id', '=', self.partner.id),
             ('name', 'like', 'Lead created from WhatsApp flow')])
        self.assertEqual(len(lead), 1)
        self.assertIn(self.flow.name, lead.name)
        self.assertEqual(lead.response_id, response)
        self.assertEqual(self.flow.send_data()['leads_generated'], 1)
        self.assertEqual(lead.phone, self.partner.whatsapp_number)
        self.assertEqual(lead.contact_name, self.partner.name)
        self.assertEqual(
            lead.source_id,
            self.env.ref('cyllo_whatsapp_automation.utm_source_whatsapp'))
        # no quotation is created for a plain template
        self.assertFalse(self.env['sale.order'].search(
            [('opportunity_id', '=', lead.id)]))

    def test_create_lead_with_quotation(self):
        template = self._create_template(
            'Order Template', template_type='custom',
            action='create_sale_order')
        response = self._create_response(
            self.flow, template, with_lines=False)
        self.env['flows.user.response.line'].create([
            {'response_id': response.id, 'field_label': 'Qty 1',
             'user_input': '3', 'product_id': self.product.id,
             'screen_id': self.flow.screen_ids[0].id},
            {'response_id': response.id, 'field_label': 'Qty 2',
             'user_input': '5', 'product_id': self.product_2.id,
             'screen_id': self.flow.screen_ids[0].id},
        ])
        response.action_create_lead()
        self.assertEqual(response.state, 'lead_created')
        lead = self.env['crm.lead'].search(
            [('partner_id', '=', self.partner.id)], order='id desc', limit=1)
        order = self.env['sale.order'].search(
            [('opportunity_id', '=', lead.id)])
        self.assertEqual(len(order), 1)
        self.assertTrue(order.whatsapp_order)
        self.assertEqual(order.partner_id, self.partner)
        self.assertEqual(
            {l.product_id: l.product_uom_qty for l in order.order_line},
            {self.product: 3.0, self.product_2: 5.0})
        # a review template with the portal link is attached to the quotation
        review = order.template_id
        self.assertTrue(review)
        self.assertEqual(review.button_url.split('/my/')[1][:6], 'orders')
        self.assertIn(order.name, review.body)
        self.assertEqual(review.header_text, 'Review Your Quotation')
