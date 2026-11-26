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
import base64
import io
import os

from PIL import Image

from odoo.exceptions import ValidationError
from odoo.tests import tagged

from .common import WhatsappAutomationCommon


@tagged('post_install', '-at_install')
class TestScreenContents(WhatsappAutomationCommon):
    """Tests for screens, contents and selection options."""

    def setUp(self):
        super().setUp()
        self.flow = self._create_flow()
        self.screen = self._create_screen(self.flow)

    def _content(self, **vals):
        values = {'screen_id': self.screen.id, 'label': 'Question'}
        values.update(vals)
        return self.env['whatsapp.flows.screen.contents'].create(values)

    def test_screen_defaults(self):
        screen = self.env['whatsapp.flows.screens'].create(
            {'name': 'Plain', 'flow_id': self.flow.id})
        self.assertEqual(screen.button_name, 'Continue')
        self.assertEqual(screen.user_id, self.env.user)

    def test_screen_deleted_with_its_contents(self):
        content = self._content(content_type='text', text='Hi')
        self.screen.content_ids.unlink()
        self.assertFalse(content.exists())

    def test_content_defaults(self):
        content = self._content()
        self.assertEqual(content.content_type, 'text')
        self.assertEqual(content.content_text_type, 'large_heading')
        self.assertEqual(content.content_text_answer_type, 'short_answer')
        self.assertEqual(content.content_selection_type, 'single_choice')
        self.assertEqual(content.shot_answer_type, 'text')
        self.assertTrue(content.required)

    def test_selection_needs_two_options(self):
        with self.assertRaisesRegex(ValidationError, 'at least two options'):
            self._content(content_type='selection', option_ids=[
                (0, 0, {'options': 'Only one'})])

    def test_selection_without_options_is_rejected(self):
        with self.assertRaises(ValidationError):
            self._content(content_type='selection')

    def test_selection_with_two_options(self):
        content = self._content(content_type='selection', option_ids=[
            (0, 0, {'options': 'Yes'}), (0, 0, {'options': 'No'})])
        self.assertEqual(content.option_ids.mapped('options'), ['Yes', 'No'])

    def test_removing_option_below_minimum_is_rejected(self):
        content = self._content(content_type='selection', option_ids=[
            (0, 0, {'options': 'Yes'}), (0, 0, {'options': 'No'})])
        with self.assertRaisesRegex(ValidationError, 'at least two options'):
            content.write({'option_ids': [(2, content.option_ids[0].id)]})

    def test_text_answer_does_not_need_options(self):
        content = self._content(content_type='text_answer')
        self.assertFalse(content.option_ids)

    def test_small_image_is_accepted(self):
        png = (b'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGP4'
               b'z8DwHwAFAAH/q842iQAAAABJRU5ErkJggg==')
        content = self._content(content_type='media', image_1920=png)
        self.assertTrue(content.image_1920)

    def test_oversized_image_is_rejected(self):
        content = self._content(content_type='media')
        buffer = io.BytesIO()
        Image.frombytes('RGB', (400, 400), os.urandom(400 * 400 * 3)).save(
            buffer, 'PNG')
        big = base64.b64encode(buffer.getvalue())
        self.assertGreater(len(buffer.getvalue()), 300 * 1024)
        with self.assertRaisesRegex(ValidationError, '300KB'):
            content.write({'image_1920': big})

    def test_option_defaults(self):
        content = self._content(content_type='selection', option_ids=[
            (0, 0, {'options': 'A'}), (0, 0, {'options': 'B'})])
        option = content.option_ids[0]
        self.assertEqual(option.content_id, content)
        self.assertEqual(option.company_id, self.env.company)
        self.assertEqual(option.user_id, self.env.user)
