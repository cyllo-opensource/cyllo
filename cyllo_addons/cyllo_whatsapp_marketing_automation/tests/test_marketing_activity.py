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
from unittest.mock import patch

from odoo.tests import common, tagged


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


@tagged('post_install', '-at_install')
class TestWhatsappMarketingExecution(common.TransactionCase):
    """Run a campaign with WhatsApp activities; the WhatsApp API is mocked."""

    SEND = ('odoo.addons.cyllo_whatsapp.models.whatsapp_template.'
            'WhatsappTemplate.action_send_template_marketing')

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.write({'token': 'tok', 'phone_uid': '123'})
        cls.partner = cls.env['res.partner'].create({
            'name': 'Campaign Customer', 'whatsapp_number': '15550001111'})
        cls.template = cls.env['whatsapp.template'].create({
            'name': 'Campaign Template',
            'template_name': 'campaign_template',
            'model_id': cls.env['ir.model']._get('marketing.activity').id,
            'body': 'Hello',
            'state': 'approved',
        })
        cls.campaign = cls.env['marketing.campaign'].create({
            'name': 'WhatsApp Execution',
            'model_id': cls.env['ir.model']._get('res.partner').id,
            'filter': str([('id', '=', cls.partner.id)]),
        })
        cls.first = cls.env['marketing.activity'].create({
            'name': 'First', 'campaign_id': cls.campaign.id,
            'type': 'whatsapp', 'whatsapp_template_id': cls.template.id,
            'activity_trigger': 0, 'trigger_schedule_type': 'begin',
        })
        cls.second = cls.env['marketing.activity'].create({
            'name': 'Second', 'campaign_id': cls.campaign.id,
            'type': 'whatsapp', 'whatsapp_template_id': cls.template.id,
            'activity_trigger': 1,
            'trigger_schedule_type': 'activity_another',
            'parent_activity_id': cls.first.id,
            'sub_parent_activity_id': cls.first.id,
        })

    def _participant_and_line(self):
        participant = self.env['marketing.participant'].create({
            'campaign_id': self.campaign.id,
            'record': 'res.partner,%s' % self.partner.id,
            'record_count': 1,
            'state': 'running',
        })
        line = self.env['marketing.activity.line'].create({
            'activity_id': self.first.id,
            'participant_id': participant.id,
            'state': 'schedule',
        })
        return participant, line

    def test_successful_send_marks_the_line_processed(self):
        participant, line = self._participant_and_line()
        with patch(self.SEND, return_value='wamid.OK') as send:
            self.first._execute_whatsapp(participant, self.first, line)
        self.assertEqual(line.state, 'processed')
        self.assertEqual(line.whatsapp_message_number, 'wamid.OK')
        self.assertEqual(send.call_args.args[-2:], ('tok', '123'))

    def test_failed_send_marks_the_line_as_error(self):
        participant, line = self._participant_and_line()
        with patch(self.SEND, side_effect=Exception('Invalid token')):
            self.first._execute_whatsapp(participant, self.first, line)
        self.assertEqual(line.state, 'error')
        self.assertIn('Invalid token', line.mail_failure_message)
        self.assertFalse(line.whatsapp_message_number)

    def test_execute_returns_a_falsy_trace_recordset(self):
        """The engine reads ``.id`` of a truthy result, so it must be empty."""
        participant, line = self._participant_and_line()
        with patch(self.SEND, return_value='wamid.OK'):
            result = self.first._execute_whatsapp(participant, self.first, line)
        self.assertEqual(result._name, 'mailing.trace')
        self.assertFalse(result)

    def test_campaign_with_chained_whatsapp_activity_runs(self):
        """A WhatsApp step with a child activity no longer breaks the run."""
        self.campaign.action_start_campaign()
        with patch(self.SEND, return_value='wamid.CHAIN'):
            self.first.marketing_execute()
        participant = self.env['marketing.participant'].search([
            ('campaign_id', '=', self.campaign.id),
            ('is_test_participant', '=', False)])
        first_line = participant.test_activity_ids.filtered(
            lambda l: l.activity_id == self.first)
        self.assertEqual(first_line.state, 'processed')
        self.assertEqual(first_line.whatsapp_message_number, 'wamid.CHAIN')


@tagged('post_install', '-at_install')
class TestWhatsappMarketingDetails(common.TransactionCase):
    """Completion counters, settings defaults, form view and translations."""

    SEND = TestWhatsappMarketingExecution.SEND

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.write({'token': 'user-token', 'phone_uid': '999'})
        cls.partner = cls.env['res.partner'].create({
            'name': 'Counter Customer', 'whatsapp_number': '15550003333'})
        cls.template = cls.env['whatsapp.template'].create({
            'name': 'Counter Template', 'template_name': 'counter_template',
            'model_id': cls.env['ir.model']._get('marketing.activity').id,
            'body': 'Hello', 'state': 'approved'})
        cls.campaign = cls.env['marketing.campaign'].create({
            'name': 'Counters',
            'model_id': cls.env['ir.model']._get('res.partner').id})
        cls.activity = cls.env['marketing.activity'].create({
            'name': 'Counter', 'campaign_id': cls.campaign.id,
            'type': 'whatsapp', 'whatsapp_template_id': cls.template.id})

    def _participant(self, count=1, test=False):
        participant = self.env['marketing.participant'].create({
            'campaign_id': self.campaign.id,
            'record': 'res.partner,%s' % self.partner.id,
            'record_count': count, 'state': 'running',
            'is_test_participant': test})
        line = self.env['marketing.activity.line'].create({
            'activity_id': self.activity.id, 'participant_id': participant.id,
            'state': 'schedule'})
        return participant, line

    def test_last_activity_completes_the_participant(self):
        participant, line = self._participant(count=1)
        with patch(self.SEND, return_value='wamid.1'):
            self.activity._execute_whatsapp(participant, self.activity, line)
        self.assertEqual(participant.record_count, 0)
        self.assertEqual(participant.state, 'completed')

    def test_participant_keeps_running_while_activities_remain(self):
        participant, line = self._participant(count=2)
        with patch(self.SEND, return_value='wamid.1'):
            self.activity._execute_whatsapp(participant, self.activity, line)
        self.assertEqual(participant.record_count, 1)
        self.assertEqual(participant.state, 'running')

    def test_test_run_never_completes_the_participant(self):
        participant, line = self._participant(count=1, test=True)
        with patch(self.SEND, return_value='wamid.1'):
            self.activity._execute_whatsapp(
                participant, self.activity, line, test=True)
        self.assertEqual(line.state, 'processed')
        self.assertEqual(participant.state, 'running')

    def test_failed_send_keeps_the_counter(self):
        participant, line = self._participant(count=1)
        with patch(self.SEND, side_effect=Exception('boom')):
            self.activity._execute_whatsapp(participant, self.activity, line)
        self.assertEqual(participant.record_count, 1)
        self.assertEqual(participant.state, 'running')

    def test_template_is_sent_to_the_participant_record(self):
        participant, line = self._participant()
        with patch(self.SEND, return_value='wamid.1') as send:
            self.activity._execute_whatsapp(participant, self.activity, line)
        record, attachment, recipient, token, phone = send.call_args.args
        self.assertEqual(record, self.activity)
        self.assertEqual(recipient, self.partner)
        self.assertEqual((token, phone), ('user-token', '999'))

    def test_attachment_is_empty_for_a_text_header_template(self):
        self.assertEqual(self.template.header_type, 'none')
        self.assertFalse(self.activity.attachment_id)

    def test_settings_default_to_the_user_credentials(self):
        defaults = self.env['res.config.settings'].default_get(
            ['phone_uid', 'token'])
        self.assertEqual(defaults['phone_uid'], '999')
        self.assertEqual(defaults['token'], 'user-token')

    def test_form_view_shows_the_whatsapp_fields_only_for_whatsapp(self):
        view = self.env.ref(
            'cyllo_whatsapp_marketing_automation.view_marketing_activity_form')
        self.assertEqual(view.model, 'marketing.activity')
        arch = view.arch
        for name in ('whatsapp_template_id', 'image_template'):
            self.assertIn('name="%s"' % name, arch)
        self.assertEqual(arch.count("type != 'whatsapp'"), 2)
        self.assertEqual(arch.count("type == 'whatsapp'"), 2)

    def test_template_domain_offers_only_approved_activity_templates(self):
        view = self.env.ref(
            'cyllo_whatsapp_marketing_automation.view_marketing_activity_form')
        self.assertIn("'state', '=', 'approved'", view.arch)
        self.assertIn("model_id.model', '=', 'marketing.activity", view.arch)

    def test_translation_files_are_complete(self):
        """Every language file has all strings translated and none fuzzy."""
        import os
        import polib
        i18n = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'i18n')
        files = [f for f in os.listdir(i18n) if f.endswith('.po')]
        self.assertTrue(files)
        for name in files:
            po = polib.pofile(os.path.join(i18n, name))
            self.assertFalse(po.untranslated_entries(), name)
            self.assertFalse(po.fuzzy_entries(), name)
