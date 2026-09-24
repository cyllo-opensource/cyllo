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
from odoo.exceptions import ValidationError


class GoogleFormQuestions(models.Model):
    _name = 'google.form.questions'
    _description = 'Google Form Questions'

    name = fields.Char(required=True, string="Question")
    google_form_id = fields.Many2one(
        'google.form', string="Google Form", ondelete='cascade'
    )
    company_id = fields.Many2one(
        'res.company',
        related='google_form_id.company_id',
        string='Company',
        store=True,
        readonly=True,
    )

    question_type = fields.Selection([
        ('TEXT', 'Short Text'),
        ('PARAGRAPH', 'Paragraph / Long Text'),
        ('EMAIL', 'Email'),
        ('PHONE', 'Phone Number'),
        ('NUMBER', 'Number'),
        ('AGE', 'Age'),
        ('DATE', 'Date'),
        ('TIME', 'Time'),
        ('ADDRESS', 'Address'),
        ('MULTIPLE_CHOICE', 'Multiple Choice (Radio)'),
        ('DROPDOWN', 'Dropdown'),
        ('CHECKBOX', 'Checkboxes (Multi-select)'),
    ], required=True, default='TEXT', string="Question Type")

    choices = fields.Text(
        string="Choices (comma-separated)",
        help="Required for Multiple Choice, Dropdown, and Checkbox question types."
    )

    lead_field_id = fields.Many2one(
        'ir.model.fields',
        domain=[('model', '=', 'crm.lead')],
        string='Map to Lead Field',
        help="Select which CRM Lead field this question's answer should be saved to."
    )

    # Computed flag used by the view to show/hide Choices textarea
    show_choices = fields.Boolean(compute='_compute_show_choices', store=False)

    _FORM_URL_RESET_FIELDS = {
        'name',
        'question_type',
        'choices',
        'lead_field_id',
        'google_form_id',
    }

    def _clear_form_url(self, forms):
        forms = forms.filtered('form_url')
        if forms:
            forms.with_context(skip_google_form_url_reset=True).write({
                'form_url': False,
            })

    def _reset_parent_form_url(self):
        self._clear_form_url(self.mapped('google_form_id'))

    @api.depends('question_type')
    def _compute_show_choices(self):
        choice_types = {'MULTIPLE_CHOICE', 'DROPDOWN', 'CHECKBOX'}
        for rec in self:
            rec.show_choices = rec.question_type in choice_types

    @api.constrains('question_type', 'choices')
    def _check_choices_required(self):
        choice_types = {'MULTIPLE_CHOICE', 'DROPDOWN', 'CHECKBOX'}
        for rec in self:
            if rec.question_type in choice_types and not (
                    rec.choices or '').strip():
                question_type_label = dict(
                    rec._fields['question_type'].selection
                ).get(rec.question_type, '')
                raise ValidationError(
                    f"Question '{rec.name}': Choices are required for "
                    f"'{question_type_label}' questions."
                )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._reset_parent_form_url()
        return records

    def write(self, vals):
        forms = self.mapped('google_form_id')
        res = super().write(vals)
        if any(field_name in vals for field_name in self._FORM_URL_RESET_FIELDS):
            self._clear_form_url(forms | self.mapped('google_form_id'))
        return res

    def unlink(self):
        forms = self.mapped('google_form_id')
        res = super().unlink()
        self._clear_form_url(forms)
        return res

