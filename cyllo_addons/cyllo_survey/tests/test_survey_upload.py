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

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


def _b64(content):
    """Return ``content`` (bytes) encoded the way the survey form sends files."""
    return base64.b64encode(content).decode()


@tagged('post_install', '-at_install')
class TestSurveyUpload(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, lang='en_US'))
        cls.survey = cls.env['survey.survey'].create({
            'title': 'Upload Survey',
            'access_mode': 'public',
            'users_login_required': False,
            'users_can_go_back': False,
            'questions_layout': 'one_page',
        })
        cls.question = cls.env['survey.question'].create({
            'survey_id': cls.survey.id,
            'title': 'Your CV',
            'question_type': 'upload',
            'constr_mandatory': True,
            'constr_error_msg': 'Please upload your CV',
        })
        cls.answer = cls.env['survey.user_input'].create({'survey_id': cls.survey.id})

    def _lines(self):
        """Return the answer lines saved for the upload question."""
        return self.answer.user_input_line_ids.filtered(lambda line: line.question_id == self.question)

    def test_validate_mandatory_missing(self):
        """A mandatory upload left empty returns the question's error message."""
        self.assertEqual(self.question.validate_question(''), {self.question.id: 'Please upload your CV'})

    def test_validate_mandatory_missing_default_message(self):
        """Without a custom message the generic one is used."""
        self.question.constr_error_msg = False
        self.assertEqual(self.question.validate_question(''), {self.question.id: 'This question requires an answer.'})

    def test_validate_missing_when_users_can_go_back(self):
        """Surveys that allow going back check mandatory answers at the end, not per page."""
        self.survey.users_can_go_back = True
        self.assertEqual(self.question.validate_question(''), {})

    def test_validate_optional_missing(self):
        """An optional upload may be left empty."""
        self.question.constr_mandatory = False
        self.assertEqual(self.question.validate_question(''), {})

    def test_validate_invalid_payloads(self):
        """Non-dict answers, bad base64, empty files and missing names are rejected."""
        invalid = {self.question.id: 'The uploaded file is not valid.'}
        for answer in ('cv.pdf', {'name': 'cv.pdf', 'data': '%%%not base64%%%'},
                       {'name': 'cv.pdf', 'data': ''}, {'name': '', 'data': _b64(b'hello')}):
            with self.subTest(answer=answer):
                self.assertEqual(self.question.validate_question(answer), invalid)

    def test_validate_size_limit(self):
        """Files up to 100 KB pass, larger ones get the size message."""
        limit = self.question._upload_max_size
        ok = {'name': 'ok.bin', 'data': _b64(b'x' * limit)}
        too_big = {'name': 'big.bin', 'data': _b64(b'x' * (limit + 1))}
        self.assertEqual(self.question.validate_question(ok), {})
        self.assertEqual(self.question.validate_question(too_big),
                         {self.question.id: 'The file must not exceed 100 KB.'})

    def test_validate_keep_existing(self):
        """Keeping the previously uploaded file is valid."""
        self.assertEqual(self.question.validate_question({'keep': True}), {})

    def test_validate_other_types_unchanged(self):
        """Other question types still use the standard validation."""
        char_question = self.env['survey.question'].create({
            'survey_id': self.survey.id,
            'title': 'Name',
            'question_type': 'char_box',
            'constr_mandatory': True,
            'constr_error_msg': 'Name please',
        })
        self.assertEqual(char_question.validate_question(''), {char_question.id: 'Name please'})

    def test_save_new_file(self):
        """Saving a file creates one upload line holding the file and its name."""
        self.answer._save_lines(self.question, {'name': 'cv.txt', 'data': _b64(b'my cv')})
        line = self._lines()
        self.assertEqual(len(line), 1)
        self.assertFalse(line.skipped)
        self.assertEqual(line.answer_type, 'upload')
        self.assertEqual(line.value_upload_name, 'cv.txt')
        self.assertEqual(base64.b64decode(line.value_upload), b'my cv')
        self.assertEqual(line.display_name, 'cv.txt')
        self.assertEqual(line._get_answer_value(), 'cv.txt')

    def test_save_keep_existing_file(self):
        """Submitting the page again without a new file keeps the stored one."""
        self.answer._save_lines(self.question, {'name': 'cv.txt', 'data': _b64(b'my cv')})
        self.answer._save_lines(self.question, {'keep': True})
        line = self._lines()
        self.assertEqual(len(line), 1)
        self.assertEqual(line.value_upload_name, 'cv.txt')
        self.assertEqual(base64.b64decode(line.value_upload), b'my cv')

    def test_save_replace_file(self):
        """A new file replaces the old one on the same line."""
        self.answer._save_lines(self.question, {'name': 'cv.txt', 'data': _b64(b'old')})
        first_line = self._lines()
        self.answer._save_lines(self.question, {'name': 'cv2.txt', 'data': _b64(b'new')})
        line = self._lines()
        self.assertEqual(line, first_line)
        self.assertEqual(line.value_upload_name, 'cv2.txt')
        self.assertEqual(base64.b64decode(line.value_upload), b'new')

    def test_save_empty_marks_skipped(self):
        """Removing the file stores the question as skipped."""
        self.answer._save_lines(self.question, {'name': 'cv.txt', 'data': _b64(b'my cv')})
        self.answer._save_lines(self.question, '')
        line = self._lines()
        self.assertEqual(len(line), 1)
        self.assertTrue(line.skipped)
        self.assertFalse(line.answer_type)
        self.assertFalse(line.value_upload)
        self.assertFalse(line.value_upload_name)

    def test_save_no_overwrite(self):
        """An existing answer cannot be overwritten when overwriting is not allowed."""
        self.answer._save_lines(self.question, {'name': 'cv.txt', 'data': _b64(b'my cv')})
        with self.assertRaises(UserError):
            self.answer._save_lines(self.question, {'name': 'cv2.txt', 'data': _b64(b'new')},
                                    overwrite_existing=False)

    def test_save_other_types_unchanged(self):
        """Other question types are still saved by the standard code."""
        char_question = self.env['survey.question'].create({
            'survey_id': self.survey.id,
            'title': 'Name',
            'question_type': 'char_box',
        })
        self.answer._save_lines(char_question, 'Alice')
        line = self.answer.user_input_line_ids.filtered(lambda line: line.question_id == char_question)
        self.assertEqual(line.answer_type, 'char_box')
        self.assertEqual(line.value_char_box, 'Alice')
