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
import hashlib

from odoo import fields, models


class DocumentLock(models.Model):
    """Model used to lock documents and do other functions for locked documents"""
    _name = 'document.lock'
    _description = 'Document Lock'
    _rec_name = 'document_file_id'

    document_file_id = fields.Many2one('document.file', help="id of document file")
    password = fields.Char(required=True, help="Password to lock document")
    validate_password_doc = fields.Char(help="Password to unlock document")
    is_lock = fields.Boolean(string="Lock", help='field for document is lock or not')

    def action_lock_doc(self):
        """Lock a document. This method allows authorized users to lock a document by setting a password for it.It
        checks if the user has the 'cyllo_documents.group_cyllo_documents_manager' group. If the user has permission, it hashes
        the provided password and sets the 'is_lock' flag to True for both the document and its associated file.
        :return: None or a notification if the user does not have permission. """
        if self.env.user.has_group('cyllo_documents.group_cyllo_documents_manager'):
            self.write({'password': hashlib.sha256(self.password.encode()).hexdigest(), 'is_lock': True})
            self.document_file_id.is_locked = True
            return {'type': 'ir.actions.act_window_close'}
        else:
            return self.show_warning("You dont have permission to lock the documents", "info")

    def action_unlock_doc(self):
        """Unlock a document. This method allows users to unlock a locked document by verifying the provided password.
        It hashes the provided password and checks if it matches the stored password for the document. If the
        passwords match, the document is unlocked, and the associated lock records are removed. If the passwords do
        not match, an incorrect password notification is displayed.
        :return: None or a notification if the password is incorrect.
        :rtype: None or dict
        """
        if self.validate_password_doc == False:
            return self.show_warning()
        if self.validate_password():
            self.document_file_id.is_locked = False
            self.env['document.lock'].search([('document_file_id', '=', self.document_file_id.id),
                                              ('is_lock', '=', True)], order="id desc").unlink()
            return {'type': 'ir.actions.act_window_close'}
        else:
            return self.show_warning()

    def action_document_share(self):
        """Share a locked document. This method allows users to share a locked document by verifying the provided
        password.It hashes the provided password and checks if it matches the stored password for the document.
        If the passwords match, the document is shared using the 'document.share' model. If the passwords do not
        match, an incorrect password notification is displayed.
        :return: URL for sharing the document or a notification
         if the password is incorrect."""
        if self.validate_password():
            return self.env['document.share'].create_url([self.document_file_id.id])
        else:
            return self.show_warning()

    def action_document_download(self):
        """Download a locked document. This method allows users to download a locked document by verifying the
        provided password.It hashes the provided password and checks if it matches the stored password for the
        document. If the passwords match, the document is downloaded using 'ir.actions.act_url'. If the passwords do
        not match, an incorrect password notification is displayed.
        :return: Action to download the document or a notification if the password is incorrect. """
        if self.validate_password():
            document_url = self.env.context.get('document_url', False)
            if self.document_file_id.extension == 'xlsx':
                return self.document_file_id.download_xlsx_record()
            else:
                return {'type': 'ir.actions.act_url', 'url': document_url + '?download=true', 'close': True}
        else:
            return self.show_warning()

    def action_document_create_lead(self):
        """Create a lead for a locked document. This method allows users to create a lead for a locked document by
         verifying the provided password. It hashes the provided password and checks if it matches the stored
         password for the document. If the passwords match, it calls the 'action_btn_create_lead' method of the
         associated document file to create a lead. If the passwords do not match, an incorrect password notification
          is displayed.
        :return: Action to create a lead, a notification for CRM module installation,or a notification for an
        incorrect password."""
        result = self.validate_password()
        if result:
            res = self.document_file_id.action_btn_create_lead(self.document_file_id.id)
            if not res:
                return self.show_warning("Install CRM Module to use this function", 'info')
            return res
        else:
            return self.show_warning()

    def action_document_create_task(self):
        """Create a task for a locked document. This method allows users to create a task for a locked document
         by verifying the provided password.It hashes the provided password and checks if it matches the stored
          password for the document. If the passwords match, it calls the 'action_btn_create_task' method of the
           associated document file to create a task. If the passwords do not match, an incorrect password
           notification is displayed.
        :return: Action to create a task, a notification for Project module
        installation,or a notification for an incorrect password."""
        if self.validate_password():
            res = self.document_file_id.action_btn_create_task(self.document_file_id.id)
            if not res:
                return self.show_warning("Install Project Module to use this function", 'info')
            return res
        else:
            return self.show_warning()

    def action_document_lock_mail(self):
        """Create mail for locked documents.This method allows users to create a mail for a locked document by
        verifying the provided password.It hashes the provided password and checks if it matches the stored password
        for the document. If the passwords match, it calls the 'on_mail_document' method of the associated document
        file to create a mail. If the passwords do not match, an incorrect password notification is displayed.
        :return: Action to create a mail or a notification for an incorrect password."""
        if self.validate_password():
            return self.document_file_id.on_mail_document([self.document_file_id.id])
        else:
            return self.show_warning()

    def action_document_copy_mail(self):
        """Copy or move locked documents. This method allows users to copy or move locked documents from one
        workspace to another by verifying the provided password. It hashes the provided password and checks if it
        matches the stored password for the document. If the passwords match, it opens a window to copy or move the
        document. If the passwords do not match, an incorrect password notification is displayed.
        :return: Action to copy or move documents or a notification for an incorrect password."""
        if self.validate_password():
            return {
                'type': 'ir.actions.act_window',
                'name': 'copy',
                'res_model': 'work.space',
                'view_mode': 'form',
                'target': 'new',
                'views': [[False, 'form']],
                'context': {'default_doc_ids': [self.document_file_id.id]}
            }
        else:
            return self.show_warning()

    def action_document_lock_archive(self):
        """ Archive locked documents after verifying the password. This method archives locked documents by checking
        the provided password against the stored password.If the passwords match, it archives the document using the
        'document_file_archive' method of the associated document file. If not, it displays an incorrect password
        notification.
        :return: Archive action or incorrect password notification."""
        if self.validate_password():
            self.document_file_id.document_file_archive(self.document_file_id.id)
            return {'type': 'ir.actions.act_window_close'}
        else:
            return self.show_warning()

    def action_document_move_to_trash(self):
        """Move locked documents to the trash folder after password verification. This method moves locked documents
        to the trash folder by verifying the provided password against the stored password. If the passwords match,
        it performs the document deletion using the 'document_file_delete' method of the associated document file.
        If not, it displays an incorrect password notification.
        :return: Trash action or incorrect password notification."""
        if self.validate_password():
            self.document_file_id.document_file_delete(self.document_file_id.id)
            return {'type': 'ir.actions.act_window_close'}
        else:
            return self.show_warning()

    def action_document_delete_permanent(self):
        """Permanently delete locked documents after password verification. This method permanently deletes locked
        documents by verifying the provided password against the stored password. If the passwords match, it deletes
        the document using the 'unlink' method of the associated document file. If not, it displays an incorrect
        password notification.
        :return: Deletion action or incorrect password notification."""
        if self.validate_password():
            self.document_file_id.unlink()
            return {'type': 'ir.actions.act_window_close'}
        else:
            return self.show_warning()

    def action_document_copy(self):
        if self.validate_password():
            return {
                'type': 'ir.actions.act_window',
                'name': 'copy',
                'res_model': 'work.space',
                'view_mode': 'form',
                'target': 'new',
                'views': [
                    [False, 'form']
                ],
                'context': {
                    'default_doc_ids': self.document_file_id.ids
                }
            }

        else:
            return self.show_warning()

    def validate_password(self):
        password = hashlib.sha256(self.validate_password_doc.encode()).hexdigest()
        self.validate_password_doc = ""
        ir_config = self.env['ir.config_parameter'].sudo()
        master_password = ir_config.get_param('cyllo_documents.document_master_password')
        if master_password:
            master_password = hashlib.sha256(master_password.encode()).hexdigest()
        is_master_admin_only = ir_config.get_param('cyllo_documents.document_master_password_admin_only')
        is_admin_user_group = self.env.user.has_group('cyllo_documents.group_cyllo_documents_manager')
        if password == self.env['document.lock'].search(
                [('document_file_id', '=', self.document_file_id.id),
                 ('is_lock', '=', True)],
                order="id desc", limit=1).password:
            return True
        if master_password and password == master_password:
            if not is_master_admin_only or is_admin_user_group:
                return True
        return False

    @staticmethod
    def show_warning(message="Incorrect Password", info_type="danger", sticky=False):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': message,
                'type': info_type,
                'sticky': sticky,
            }
        }