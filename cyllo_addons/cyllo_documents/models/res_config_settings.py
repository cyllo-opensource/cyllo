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
from odoo import _, api, fields, models


class ResConfigSettings(models.TransientModel):
    """ Inherited res.config.settings to add trash limit field"""
    _inherit = 'res.config.settings'

    trash = fields.Integer(string='Trash Limit', default=30, help="set the time limit for the deleted files",
                           config_parameter='cyllo_documents.trash')
    sync_google_drive = fields.Boolean(string="Sync With Google Drive", help="checkbox to sync with Google Drive",
                                       config_parameter='cyllo_documents.sync_google_drive')
    sync_one_drive = fields.Boolean(string="Sync With One Drive", help="checkbox to sync with One Drive",
                                    config_parameter='cyllo_documents.sync_one_drive')
    auto_sync_google_drive = fields.Integer(help='set time limit to auto sync your google drive', default=1,
                                            config_parameter='cyllo_documents.auto_sync_google_drive')
    auto_sync_one_drive = fields.Integer(help='set time limit to auto sync your one drive', default=1,
                                         config_parameter='cyllo_documents.auto_sync_one_drive')
    sync_google_workspace = fields.Boolean(help='checkbox to sync workspace with Google Drive',
                                           config_parameter='cyllo_documents.sync_google_workspace')
    sync_one_drive_workspace = fields.Boolean(string='Sync OneDrive Workspace',
                                              help='checkbox to sync workspace with Onedrive',
                                              config_parameter='cyllo_documents.sync_one_drive_workspace')
    module_crm = fields.Boolean(string='Create lead', help='Enable to create lead from documents',
                                config_parameter='cyllo_documents.module_crm')
    module_project = fields.Boolean(string='Create task', help='Enable to create task from documents',
                                    config_parameter='cyllo_documents.module_project')
    document_master_password = fields.Char(string='Master Password', help='Master Password',
                                           config_parameter="cyllo_documents.document_master_password")
    document_master_password_admin_only = fields.Boolean(string='Master Password Admin Only',
                                                         help='Indicates if the locked records can only be opened by admins even with the Master password.',
                                                         config_parameter="cyllo_documents.document_master_password_admin_only")

    @api.model_create_multi
    def create(self, vals_list):
        """Create method to set scheduled action's interval number for Google Drive and OneDrive synchronization.
        This method is used to create or update the interval number of scheduled actions for Google Drive and
        OneDrive synchronization based on the provided configuration values.
        Args:
            vals_list (list): List of dictionaries containing values to create the configuration settings.
        Returns:
            RecordSet: The created configuration settings record."""
        self.env.ref('cyllo_documents.ir_cron_sync_google_drive').sudo().write(
            {'interval_type': 'days', 'interval_number': vals_list[0].get('auto_sync_google_drive')})
        self.env.ref('cyllo_documents.ir_cron_sync_one_drive').sudo().write(
            {'interval_type': 'days', 'interval_number': vals_list[0].get('auto_sync_one_drive')})
        self.is_crm_installed(vals_list)
        self.is_project_installed(vals_list)
        res = super(ResConfigSettings, self).create(vals_list)
        return res

    def action_google_drive_accounts(self):
        """Action to redirect to the Google Drive Connector. This function defines an action to open the Google
        Drive Connector in tree and form view mode.
        Returns:
            dict: A dictionary defining the action to open the Google Drive Connector."""
        return {
            'type': 'ir.actions.act_window',
            'name': _("Google Drive Accounts"),
            'res_model': 'google.drive.connector',
            'view_mode': 'tree,form',
            'target': 'current',
        }

    def action_one_drive_accounts(self):
        """Action to redirect to the OneDrive Connector. This function defines an action to open the OneDrive
        Connector in tree and form view mode.
        Returns:
            dict: A dictionary defining the action to open the OneDrive Connector."""
        return {
            'type': 'ir.actions.act_window',
            'name': _("One Drive Accounts"),
            'res_model': 'one.drive.connector',
            'view_mode': 'tree,form',
            'target': 'current',
        }

    def action_sync_now_google(self):
        """Action to call auto sync Google Drive manually while clicking sync now"""
        self.env['google.drive.connector'].auto_sync_google_drive()

    def action_sync_now_onedrive(self):
        """Action to call auto sync One Drive manually while clicking sync now"""
        self.env['one.drive.connector'].auto_sync_one_drive()

    def is_crm_installed(self, vals_list):
        """ Set 'is_crm_install' field for all 'document.file' records.
            Args: vals_list (list): List of dictionaries containing values.
            Returns: None """
        records = self.env['document.file'].search([])
        is_crm_install = vals_list[0].get('module_crm')
        for record in records:
            record.write({'is_crm_install': is_crm_install})

    def is_project_installed(self, vals_list):
        """ Set 'is_project_install' field for all 'document.file' records.
            Args: vals_list (list): List of dictionaries containing values.
            Returns: None"""
        records = self.env['document.file'].search([])
        is_project_install = vals_list[0].get('module_project')
        for record in records:
            record.write({'is_project_install': is_project_install})
