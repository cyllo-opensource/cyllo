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
from odoo.tests import common


class TestWhatsappMarketingActivity(common.TransactionCase):
    """Tests for the WhatsApp activity type of marketing automation."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_model = cls.env['ir.model']._get('res.partner')
        cls.campaign = cls.env['marketing.campaign'].create({
            'name': 'Cyllo WhatsApp Campaign',
            'model_id': cls.partner_model.id,
        })

    # -------------------------------------------------------------------------
    # Model extensions
    # -------------------------------------------------------------------------
    def test_whatsapp_is_an_activity_type(self):
        """WhatsApp is offered alongside the standard activity types."""
        selection = dict(
            self.env['marketing.activity']._fields['type'].selection)
        self.assertIn('whatsapp', selection)
        self.assertEqual(selection['whatsapp'], 'Whatsapp Message')

    def test_whatsapp_template_field(self):
        """The activity points at a WhatsApp template."""
        field = self.env['marketing.activity']._fields.get(
            'whatsapp_template_id')
        self.assertTrue(field)
        self.assertEqual(field.comodel_name, 'whatsapp.template')

    def test_activity_line_stores_the_message_id(self):
        """Each processed line keeps the WhatsApp message identifier."""
        field = self.env['marketing.activity.line']._fields.get(
            'whatsapp_message_number')
        self.assertTrue(field)
        self.assertEqual(field.type, 'char')

    def test_execute_whatsapp_helper_exists(self):
        """The activity model exposes the WhatsApp execution hook."""
        self.assertTrue(hasattr(self.env['marketing.activity'],
                                '_execute_whatsapp'))

    # -------------------------------------------------------------------------
    # Activity records
    # -------------------------------------------------------------------------
    def test_whatsapp_activity_can_be_created(self):
        """A campaign step can be configured as a WhatsApp message."""
        activity = self.env['marketing.activity'].create({
            'name': 'Send WhatsApp Welcome',
            'campaign_id': self.campaign.id,
            'type': 'whatsapp',
        })
        self.assertEqual(activity.type, 'whatsapp')
        self.assertFalse(activity.attachment_id)

    def test_default_activity_type_is_mail(self):
        """Adding the WhatsApp type does not change the default."""
        activity = self.env['marketing.activity'].create({
            'name': 'Send Mail',
            'campaign_id': self.campaign.id,
        })
        self.assertEqual(activity.type, 'mail')

    def test_attachment_stays_empty_without_a_document_template(self):
        """No attachment is generated when the template has no document header."""
        activity = self.env['marketing.activity'].create({
            'name': 'WhatsApp No Header',
            'campaign_id': self.campaign.id,
            'type': 'whatsapp',
        })
        activity.invalidate_recordset(['attachment_id'])
        self.assertFalse(activity.attachment_id)


class TestWhatsappMarketingSettings(common.TransactionCase):
    """Tests for the WhatsApp cloud credentials in the settings."""

    def test_settings_fields_are_declared(self):
        """The phone number id and access token are configurable."""
        fields = self.env['res.config.settings']._fields
        self.assertIn('phone_uid', fields)
        self.assertIn('token', fields)

    def test_credentials_are_persisted(self):
        """Saving the settings stores both credentials as parameters."""
        self.env['res.config.settings'].create({
            'phone_uid': '1234567890',
            'token': 'EAAG-test-token',
        }).execute()
        params = self.env['ir.config_parameter'].sudo()
        self.assertEqual(
            params.get_param('cyllo_whatsapp_marketing_automation.phone_uid'),
            '1234567890')
        self.assertEqual(
            params.get_param('cyllo_whatsapp_marketing_automation.token'),
            'EAAG-test-token')
