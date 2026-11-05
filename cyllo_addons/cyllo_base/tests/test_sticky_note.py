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
import json

from odoo.tests import common


class TestStickyNotes(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.sticky_note = cls.env['sticky.note'].create({
            'title': 'Test note',
            'description': 'This note is created to test',
            'company_id': cls.env.company.id
        })

    def test_edit_note(self):
        args = {
            'title': 'Edited title',
            'description': 'Edited description',
            'drawing': 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==',
            'id': self.sticky_note.id
        }
        self.sticky_note.edit_note(args)
        self.assertEqual(self.sticky_note.title, 'Edited title')
        self.assertEqual(self.sticky_note.description, 'Edited description')
        self.assertTrue(self.sticky_note.drawing.startswith('data:image/png;base64'))

    def test_edit_note_images(self):
        images = [{
            'name': 'diagram.png',
            'data': 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==',
        }]
        args = {
            'images': json.dumps(images),
            'id': self.sticky_note.id,
        }
        self.sticky_note.edit_note(args)
        stored_images = json.loads(self.sticky_note.images)
        self.assertEqual(len(stored_images), 1)
        self.assertEqual(stored_images[0]['name'], 'diagram.png')

    def test_pin_to_view(self):
        args = {
            'pin_scope': 'view',
            'pinned_action_key': '123',
            'pinned_view_type': 'list',
            'id': self.sticky_note.id,
        }
        self.sticky_note.edit_note(args)
        self.assertEqual(self.sticky_note.pin_scope, 'view')
        self.assertEqual(self.sticky_note.pinned_action_key, '123')
        self.assertEqual(self.sticky_note.pinned_view_type, 'list')
        self.assertFalse(self.sticky_note.pinned_res_model)
        self.assertFalse(self.sticky_note.pinned_res_id)

    def test_pin_to_record(self):
        args = {
            'pin_scope': 'record',
            'pinned_res_model': 'sale.order',
            'pinned_res_id': 42,
            'id': self.sticky_note.id,
        }
        self.sticky_note.edit_note(args)
        self.assertEqual(self.sticky_note.pin_scope, 'record')
        self.assertEqual(self.sticky_note.pinned_res_model, 'sale.order')
        self.assertEqual(self.sticky_note.pinned_res_id, 42)

    def test_unpin(self):
        self.sticky_note.edit_note({
            'pin_scope': 'record',
            'pinned_res_model': 'sale.order',
            'pinned_res_id': 42,
            'id': self.sticky_note.id,
        })
        self.sticky_note.edit_note({
            'pin_scope': False,
            'pinned_res_model': False,
            'pinned_res_id': False,
            'id': self.sticky_note.id,
        })
        self.assertFalse(self.sticky_note.pin_scope)
        self.assertFalse(self.sticky_note.pinned_res_model)
        self.assertFalse(self.sticky_note.pinned_res_id)
