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
        args = {'title': 'Edited title', 'description': 'Edited description', 'id': self.sticky_note.id}
        self.sticky_note.edit_note(args)
        self.assertEqual(self.sticky_note.title, 'Edited title')
        self.assertEqual(self.sticky_note.description, 'Edited description')
