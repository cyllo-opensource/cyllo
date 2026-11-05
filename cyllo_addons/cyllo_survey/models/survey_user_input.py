# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cyllo(<https://www.cyllo.com>)
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
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SurveyUserInput(models.Model):
    _inherit = 'survey.user_input'

    def _save_lines(self, question, answer, comment=None, overwrite_existing=True):
        if question.question_type != 'upload':
            return super()._save_lines(question, answer, comment, overwrite_existing)
        return self._save_line_upload(question, answer, overwrite_existing)

    def _save_line_upload(self, question, answer, overwrite_existing):
        """Store the uploaded file, keeping the previous one when the participant did not replace it."""
        old_answers = self.env['survey.user_input.line'].search([
            ('user_input_id', '=', self.id),
            ('question_id', '=', question.id)
        ])
        if isinstance(answer, dict) and answer.get('keep') and old_answers.filtered('value_upload'):
            return old_answers
        if old_answers and not overwrite_existing:
            raise UserError(_("This answer cannot be overwritten."))

        vals = {
            'user_input_id': self.id,
            'question_id': question.id,
            'skipped': True,
            'answer_type': False,
            'value_upload': False,
            'value_upload_name': False,
        }
        if isinstance(answer, dict) and answer.get('data'):
            vals.update(
                skipped=False,
                answer_type='upload',
                value_upload=answer['data'],
                value_upload_name=answer.get('name'),
            )
        if old_answers:
            old_answers.write(vals)
            return old_answers
        return self.env['survey.user_input.line'].create(vals)


class SurveyUserInputLine(models.Model):
    _inherit = 'survey.user_input.line'

    answer_type = fields.Selection(
        selection_add=[('upload', 'File')],
        ondelete={'upload': 'cascade'})
    value_upload = fields.Binary('File answer', attachment=True)
    value_upload_name = fields.Char('File name')

    @api.depends('value_upload_name')
    def _compute_display_name(self):
        super()._compute_display_name()
        for line in self.filtered(lambda line: line.answer_type == 'upload' and line.value_upload_name):
            line.display_name = line.value_upload_name

    def _get_answer_value(self):
        self.ensure_one()
        if self.answer_type == 'upload':
            return self.value_upload_name
        return super()._get_answer_value()
