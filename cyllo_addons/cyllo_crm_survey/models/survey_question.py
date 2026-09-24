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
from odoo import models, fields, api


class SurveyQuestion(models.Model):
    _inherit = 'survey.question'

    lead_field_id = fields.Many2one(
        'ir.model.fields',
        string='Lead Field',
        help="Select the CRM Lead field to map this question's answer to."
    )

    lead_field_domain = fields.Char(
        compute='_compute_lead_field_domain',
        readonly=True,
        store=False
    )

    @api.depends('question_type')
    def _compute_lead_field_domain(self):
        """Compute dynamic domain for lead_field_id based on question_type."""
        for record in self:
            domain = [('model', '=', 'crm.lead')]
            type_mapping = {
                'free_text': ['char', 'text', 'many2one'],
                'text_box': ['char', 'text', 'many2one'],
                'char_box': ['char', 'many2one'],
                'numerical_box': ['integer', 'float', 'monetary'],
                'date': ['date'],
                'datetime': ['datetime'],
                'simple_choice': ['selection', 'many2one'],
                'multiple_choice': ['many2many', 'selection'],
                'matrix': [],
            }
            allowed_types = type_mapping.get(record.question_type, [])
            if allowed_types:
                domain.append(('ttype', 'in', allowed_types))
            else:
                domain.append(('id', '=', False))
            record.lead_field_domain = str(domain)

    @api.onchange('question_type')
    def _onchange_question_type(self):
        """Clear lead_field_id if it's no longer valid for the new question_type."""
        type_mapping = {
            'free_text': ['char', 'text'],
            'text_box': ['char', 'text'],
            'char_box': ['char'],
            'numerical_box': ['integer', 'float', 'monetary'],
            'date': ['date'],
            'datetime': ['datetime'],
            'simple_choice': ['selection', 'many2one'],
            'multiple_choice': ['many2many', 'selection'],
            'matrix': [],
        }

        allowed_types = type_mapping.get(self.question_type, [])
        if self.lead_field_id:
            if self.lead_field_id.ttype not in allowed_types:
                self.lead_field_id = False