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
from odoo import fields, _
from odoo.tests.common import TransactionCase


class TestDocumentTrash(TransactionCase):

    def test_action_restore_document(self):
        trash_doc = self.env['document.trash'].create({
            'name': 'Test Document',
            'date': fields.Datetime.now(),
                    'workspace_id': self.env['document.workspace'].create({
                    'name': 'Test Workspace',
                }).id,
            'user_id': self.env.user.id,
        })
        self.assertEqual(trash_doc.action_restore_document(), {
            'name': _('Trash'),
            'target': 'main',
            'view_mode': 'tree,form',
            'res_model': 'document.trash',
            'type': 'ir.actions.act_window',
        })
        
