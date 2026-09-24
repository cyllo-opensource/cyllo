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
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError

class TestGoogleFormQuestions(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.form = cls.env['google.form'].create({
            'name': 'Test Form',
        })
        cls.form.with_context(skip_google_form_url_reset=True).write({
            'form_url': 'http://test.url',
            'google_form_id': '12345'
        })

    def test_question_creation_resets_form_url(self):
        """Test creating a question resets the parent form URL"""
        self.assertEqual(self.form.form_url, 'http://test.url')
        self.env['google.form.questions'].create({
            'name': 'What is your name?',
            'google_form_id': self.form.id,
            'question_type': 'TEXT',
        })
        self.assertFalse(self.form.form_url)

    def test_choices_required_for_choice_types(self):
        """Test choices are required for MULTIPLE_CHOICE, DROPDOWN, CHECKBOX"""
        with self.assertRaises(ValidationError):
            self.env['google.form.questions'].create({
                'name': 'Select option',
                'google_form_id': self.form.id,
                'question_type': 'MULTIPLE_CHOICE',
                'choices': '',
            })
        # Should pass if choices provided
        question = self.env['google.form.questions'].create({
            'name': 'Select option',
            'google_form_id': self.form.id,
            'question_type': 'MULTIPLE_CHOICE',
            'choices': 'Option 1, Option 2',
        })
        self.assertTrue(question.id)

    def test_question_deletion_resets_form_url(self):
        """Test deleting a question resets parent form URL"""
        question = self.env['google.form.questions'].create({
            'name': 'Age',
            'google_form_id': self.form.id,
            'question_type': 'AGE',
        })
        self.form.with_context(skip_google_form_url_reset=True).write({
            'form_url': 'http://test.url',
            'google_form_id': '12345'
        })
        self.assertEqual(self.form.form_url, 'http://test.url')
        question.unlink()
        self.assertFalse(self.form.form_url)
