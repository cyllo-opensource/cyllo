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
from odoo import fields, models


class BackupDestination(models.Model):
    """DbBackup provides an interface to manage database
       backups of Local Server, Remote Server, Google Drive, Dropbox, Onedrive,
       Nextcloud and Amazon S3"""
    _name = 'backup.destination'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Database Backup Destination'

    name = fields.Char(help='Name of the location type')
    image = fields.Binary(help='Logo of backup destination')
    code = fields.Char(help='Code for destination locations')

    def action_create_request(self):
        """ This method is used to initiate a request for db backup creation"""
        return {
            "type": "ir.actions.act_window",
            "res_model": "db.backup.configure",
            'view_mode': 'form',
            "name": 'Backup Creation',
            "domain": [('backup_destination', '=', self.code)],
            "context": {
                'default_backup_destination': self.code,
            },
        }

    def action_view_configurations(self):
        """ This method is used to list configuration when clicking the kanban card"""
        return {
            "type": "ir.actions.act_window",
            "res_model": "db.backup.configure",
            'view_mode': 'tree,form',
            "name": 'Backup Creation',
            "domain": [('backup_destination', '=', self.code)],
            "context": {
                'default_backup_destination': self.code,
            },
        }
