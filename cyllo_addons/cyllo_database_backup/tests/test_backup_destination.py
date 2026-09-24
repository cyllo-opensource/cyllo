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

class TestBackupDestination(TransactionCase):
    """Test methods of the Backup Destination"""

    @classmethod
    def setUpClass(cls):
        """Set up class values"""
        super().setUpClass()
        cls.backup_dest = cls.env['backup.destination'].create({
            'name': 'Test Destination',
            'code': 'abc'})

    def test_action_create_request(self):
        self.assertEqual(self.backup_dest.action_create_request(), {
            "type": "ir.actions.act_window",
            "res_model": "db.backup.configure",
            'view_mode': 'form',
            "name": 'Backup Creation',
            "domain": [('backup_destination', '=', self.backup_dest.code)],
            "context": {
                'default_backup_destination': self.backup_dest.code,
            },
        })

    def test_action_view_configurations(self):
        self.assertEqual(self.backup_dest.action_view_configurations(), {
            "type": "ir.actions.act_window",
            "res_model": "db.backup.configure",
            'view_mode': 'tree,form',
            "name": 'Backup Creation',
            "domain": [('backup_destination', '=', self.backup_dest.code)],
            "context": {
                'default_backup_destination': self.backup_dest.code,
            },
        })
