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
##############################################################################
from odoo.tests.common import TransactionCase

class TestCrmSurvey(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.partner = cls.env['res.partner'].create({'name': 'Test Partner'})
        cls.lead = cls.env['crm.lead'].create({
            'name': 'Test Lead',
            'partner_id': cls.partner.id,
        })
        cls.survey = cls.env['survey.survey'].create({
            'title': 'Test Survey',
            'lead_id': cls.lead.id,
            'create_lead': True,
        })
        cls.field_char = cls.env['ir.model.fields'].search([('model', '=', 'crm.lead'), ('name', '=', 'name')], limit=1)
        cls.field_phone = cls.env['ir.model.fields'].search([('model', '=', 'crm.lead'), ('name', '=', 'phone')], limit=1)
        cls.question_char = cls.env['survey.question'].create({
            'survey_id': cls.survey.id,
            'title': 'What is your name?',
            'question_type': 'char_box',
            'lead_field_id': cls.field_char.id,
        })

    def test_crm_lead_survey_count(self):
        """Test survey count on crm lead"""
        self.lead._compute_survey_count()
        self.assertEqual(self.lead.survey_count, 1)

    def test_survey_survey_action_send(self):
        """Test action_send_survey context"""
        action = self.survey.with_context(default_lead_id=self.lead.id).action_send_survey()
        self.assertIn('default_partner_ids', action['context'])
        self.assertEqual(action['context']['default_partner_ids'], [(6, 0, [self.partner.id])])

    def test_survey_question_onchange_type(self):
        """Test onchange question type resets invalid lead field"""
        self.assertEqual(self.question_char.lead_field_id, self.field_char)
        self.question_char.question_type = 'numerical_box'
        self.question_char._onchange_question_type()
        self.assertFalse(self.question_char.lead_field_id)

    def test_survey_user_input_mark_done_creates_lead(self):
        """Test marking survey as done creates a lead with mapped fields"""
        user_input = self.env['survey.user_input'].create({
            'survey_id': self.survey.id,
            'partner_id': self.partner.id,
            'test_entry': False,
        })
        self.env['survey.user_input.line'].create({
            'user_input_id': user_input.id,
            'question_id': self.question_char.id,
            'answer_type': 'char_box',
            'value_char_box': 'Custom Lead Name',
        })
        leads_before = self.env['crm.lead'].search_count([])
        user_input._mark_done()
        leads_after = self.env['crm.lead'].search_count([])
        self.assertEqual(leads_after, leads_before + 1)
        new_lead = self.env['crm.lead'].search([], order='id desc', limit=1)
        self.assertEqual(new_lead.name, 'Custom Lead Name')
        self.assertEqual(new_lead.partner_id, self.partner)
