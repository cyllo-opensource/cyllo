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
from odoo import fields
from odoo.tests import common


class TestDocumentRequestTemplate(common.TransactionCase):
    """Test class for document.request.template related methods."""

    def test_compute_user_ids(self):
        """Test getting managers."""
        manager = self.env['res.users'].create({
            'name': 'Test Manager',
            'login': 'testmanager',
        })
        manager.write({'groups_id': [fields.Command.link(self.env.ref('cyllo_documents.group_cyllo_documents_manager').id)]})
        document_request = self.env['document.request.template'].create({
            'name': 'Test Template',
            'manager_id': manager.id,
        })
        document_request._compute_user_ids()
        self.assertIn(manager.id, document_request.user_ids.ids)
