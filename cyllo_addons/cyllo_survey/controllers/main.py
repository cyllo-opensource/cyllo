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
from werkzeug.exceptions import NotFound

from odoo import http
from odoo.http import request

from odoo.addons.survey.controllers.main import Survey


class SurveyUpload(Survey):

    @http.route('/survey/upload/<string:survey_token>/<string:answer_token>/<int:line_id>',
                type='http', auth='public', website=True, sitemap=False)
    def survey_upload_download(self, survey_token, answer_token, line_id):
        """Download the file a participant uploaded as an answer."""
        access_data = self._get_access_data(survey_token, answer_token, ensure_token=True, check_partner=False)
        if access_data['validity_code'] is not True and not access_data['has_survey_access']:
            raise NotFound()
        line = access_data['answer_sudo'].user_input_line_ids.filtered(
            lambda line: line.id == line_id and line.answer_type == 'upload')
        if not line:
            raise NotFound()
        return request.env['ir.binary']._get_stream_from(
            line, 'value_upload', filename_field='value_upload_name'
        ).get_response(as_attachment=True)
