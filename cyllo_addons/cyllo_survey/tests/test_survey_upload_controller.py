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
import base64
import re

from odoo.tests import tagged
from odoo.tests.common import HttpCase


@tagged('post_install', '-at_install')
class TestSurveyUploadController(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.survey = cls.env['survey.survey'].create({
            'title': 'Upload Survey',
            'access_mode': 'public',
            'users_login_required': False,
            'questions_layout': 'one_page',
        })
        cls.question = cls.env['survey.question'].create({
            'survey_id': cls.survey.id,
            'title': 'Your CV',
            'question_type': 'upload',
            'constr_mandatory': True,
        })

    def _start(self):
        """Open the survey as a public visitor and return (answer, csrf_token)."""
        response = self.url_open('/survey/start/%s' % self.survey.access_token)
        self.assertEqual(response.status_code, 200)
        answer = self.env['survey.user_input'].search([('survey_id', '=', self.survey.id)], order='id desc', limit=1)
        csrf_token = re.search(r'name="csrf_token" value="([^"]+)"', response.text).group(1)
        self.opener.post('%s/survey/begin/%s/%s' % (self.base_url(), self.survey.access_token, answer.access_token), json={})
        return answer, csrf_token

    def _submit(self, answer, csrf_token, value):
        """Submit the upload question with ``value`` and return the JSON-RPC result."""
        response = self.opener.post(
            '%s/survey/submit/%s/%s' % (self.base_url(), self.survey.access_token, answer.access_token),
            json={'params': {self.question.id: value, 'csrf_token': csrf_token, 'token': answer.access_token}})
        self.assertEqual(response.status_code, 200)
        return response.json()['result']

    def _download(self, answer, line_id):
        """Call the upload download route."""
        return self.url_open('/survey/upload/%s/%s/%s' % (self.survey.access_token, answer.access_token, line_id))

    def test_submit_and_download(self):
        """A file submitted through the survey is stored and can be downloaded."""
        answer, csrf_token = self._start()
        self._submit(answer, csrf_token, {'name': 'cv.txt', 'data': base64.b64encode(b'my cv').decode()})
        answer.invalidate_recordset()
        line = answer.user_input_line_ids.filtered(lambda l: l.answer_type == 'upload')
        self.assertEqual(line.value_upload_name, 'cv.txt')
        self.assertEqual(answer.state, 'done')

        response = self._download(answer, line.id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'my cv')
        self.assertIn('attachment', response.headers.get('Content-Disposition', ''))
        self.assertIn('cv.txt', response.headers.get('Content-Disposition', ''))

    def test_submit_too_big(self):
        """A file over the limit is refused with a validation error and nothing is saved."""
        answer, csrf_token = self._start()
        too_big = base64.b64encode(b'x' * (self.question._upload_max_size + 1)).decode()
        result = self._submit(answer, csrf_token, {'name': 'big.bin', 'data': too_big})
        self.assertEqual(result[1]['error'], 'validation')
        self.assertIn(str(self.question.id), result[1]['fields'])
        answer.invalidate_recordset()
        self.assertFalse(answer.user_input_line_ids)
        self.assertEqual(answer.state, 'in_progress')

    def test_download_not_found(self):
        """Unknown lines, other answers' lines and wrong tokens give 404."""
        answer, csrf_token = self._start()
        self._submit(answer, csrf_token, {'name': 'cv.txt', 'data': base64.b64encode(b'my cv').decode()})
        answer.invalidate_recordset()
        line = answer.user_input_line_ids.filtered(lambda l: l.answer_type == 'upload')
        other_answer = self.env['survey.user_input'].create({'survey_id': self.survey.id})

        self.assertEqual(self._download(answer, line.id + 1000).status_code, 404)
        self.assertEqual(self._download(other_answer, line.id).status_code, 404)
        response = self.url_open('/survey/upload/%s/%s/%s' % (self.survey.access_token, 'wrong-token', line.id))
        self.assertEqual(response.status_code, 404)
