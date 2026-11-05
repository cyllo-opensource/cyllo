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
import base64
import binascii

from odoo import _, fields, models


class SurveyQuestion(models.Model):
    _inherit = 'survey.question'

    _upload_max_size = 100 * 1024

    question_type = fields.Selection(
        selection_add=[('upload', 'Upload File')],
        ondelete={'upload': lambda records: records.write({'question_type': 'char_box'})})

    def validate_question(self, answer, comment=None):
        if self.question_type != 'upload':
            return super().validate_question(answer, comment)
        return self._validate_upload(answer)

    def _validate_upload(self, answer):
        """Check that a mandatory file is given and that it fits the size limit."""
        self.ensure_one()
        if not answer:
            if self.constr_mandatory and not self.survey_id.users_can_go_back:
                return {self.id: self.constr_error_msg or _('This question requires an answer.')}
            return {}
        if not isinstance(answer, dict):
            return {self.id: _('The uploaded file is not valid.')}
        if answer.get('keep'):
            return {}
        try:
            size = len(base64.b64decode(answer.get('data') or '', validate=True))
        except (binascii.Error, ValueError):
            return {self.id: _('The uploaded file is not valid.')}
        if not size or not answer.get('name'):
            return {self.id: _('The uploaded file is not valid.')}
        if size > self._upload_max_size:
            return {self.id: _('The file must not exceed %s KB.', self._upload_max_size // 1024)}
        return {}
