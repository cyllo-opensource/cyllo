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
from odoo.exceptions import ValidationError
from odoo.tests import tagged

from .common import WhatsappAutomationCommon


@tagged('post_install', '-at_install')
class TestSaleOrderTemplate(WhatsappAutomationCommon):
    """Tests for the WhatsApp additions to `sale.order.template`."""

    def setUp(self):
        super().setUp()
        self.quotation_template = self.env['sale.order.template'].create({
            'name': 'Starter Pack',
            'sale_order_template_line_ids': [
                (0, 0, {'name': self.product.name,
                        'product_id': self.product.id,
                        'product_uom_qty': 1,
                        'product_uom_id': self.product.uom_id.id}),
                (0, 0, {'name': self.product_2.name,
                        'product_id': self.product_2.id,
                        'product_uom_qty': 1,
                        'product_uom_id': self.product_2.uom_id.id}),
            ],
        })

    # -- flow generation ----------------------------------------------------
    def test_create_flow_requires_products(self):
        empty = self.env['sale.order.template'].create({'name': 'Empty'})
        with self.assertRaises(ValidationError):
            empty.action_create_whatsapp_flow()
        self.assertFalse(empty.flow_id)

    def test_create_flow_one_screen_per_product(self):
        self.quotation_template.action_create_whatsapp_flow()
        flow = self.quotation_template.flow_id
        self.assertTrue(flow)
        self.assertIn(self.quotation_template.name, flow.name)
        self.assertEqual(flow.screen_ids.mapped('name'),
                         [self.product.name, self.product_2.name])
        self.assertEqual(set(flow.screen_ids.mapped('button_name')), {'Next'})

    def test_create_flow_screen_contents(self):
        self.quotation_template.action_create_whatsapp_flow()
        screen = self.quotation_template.flow_id.screen_ids[0]
        types = screen.content_ids.mapped('content_type')
        # no product image -> heading, description and the quantity input
        self.assertEqual(types, ['text', 'text', 'text_answer'])
        heading, description, quantity = screen.content_ids
        self.assertEqual(heading.text, self.product.name)
        self.assertEqual(description.text, 'A product sold from WhatsApp')
        self.assertEqual(quantity.product_id, self.product)
        self.assertEqual(quantity.shot_answer_type, 'number')
        self.assertFalse(quantity.required)

    def test_create_flow_default_description(self):
        self.quotation_template.action_create_whatsapp_flow()
        screen = self.quotation_template.flow_id.screen_ids[1]
        self.assertEqual(screen.content_ids[1].text, 'No description available.')

    def test_create_flow_adds_media_when_product_has_image(self):
        png = (b'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGP4'
               b'z8DwHwAFAAH/q842iQAAAABJRU5ErkJggg==')
        self.product.image_1920 = png
        self.quotation_template.action_create_whatsapp_flow()
        screen = self.quotation_template.flow_id.screen_ids[0]
        self.assertEqual(screen.content_ids[0].content_type, 'media')
        self.assertEqual(len(screen.content_ids), 4)

    # -- template creation -------------------------------------------------
    def test_create_template_requires_flow(self):
        with self.assertRaisesRegex(ValidationError, 'create a whatsapp flow'):
            self.quotation_template.action_create_whatsapp_template()

    def test_create_template_requires_published_flow(self):
        self.quotation_template.action_create_whatsapp_flow()
        with self.assertRaisesRegex(ValidationError, 'must be published'):
            self.quotation_template.action_create_whatsapp_template()

    def test_create_template_action(self):
        self.quotation_template.action_create_whatsapp_flow()
        self.quotation_template.flow_id.state = 'published'
        action = self.quotation_template.action_create_whatsapp_template()
        self.assertEqual(action['res_model'], 'whatsapp.template')
        self.assertEqual(action['target'], 'new')
        ctx = action['context']
        self.assertEqual(ctx['default_template_type'], 'flows')
        self.assertEqual(ctx['default_flows_id'],
                         self.quotation_template.flow_id.id)
        self.assertEqual(ctx['default_action'], 'create_sale_order')

    # -- view / remove / send ----------------------------------------------
    def test_view_flow_action(self):
        flow = self._create_flow()
        self.quotation_template.flow_id = flow
        action = self.quotation_template.action_view_flow()
        self.assertEqual(action['res_model'], 'whatsapp.flows')
        self.assertEqual(action['res_id'], flow.id)

    def test_view_template_action(self):
        template = self._create_template()
        self.quotation_template.template_id = template
        action = self.quotation_template.action_view_template()
        self.assertEqual(action['res_model'], 'whatsapp.template')
        self.assertEqual(action['res_id'], template.id)

    def test_remove_template(self):
        self.quotation_template.template_id = self._create_template()
        self.quotation_template.action_remove_wa_template()
        self.assertFalse(self.quotation_template.template_id)

    def test_send_requires_approved_template(self):
        self.quotation_template.template_id = self._create_template(
            state='pending')
        with self.assertRaisesRegex(ValidationError, 'not yet approved'):
            self.quotation_template.action_send_whatsapp_template()

    def test_send_opens_wizard_for_approved_template(self):
        template = self._create_template(state='approved')
        self.quotation_template.template_id = template
        action = self.quotation_template.action_send_whatsapp_template()
        self.assertEqual(action['res_model'], 'whatsapp.template.message')
        self.assertEqual(action['context']['default_wa_template_id'],
                         template.id)

    def test_flow_and_template_are_not_copied(self):
        self.quotation_template.flow_id = self._create_flow()
        self.quotation_template.template_id = self._create_template()
        copy = self.quotation_template.copy()
        self.assertFalse(copy.flow_id)
        self.assertFalse(copy.template_id)
