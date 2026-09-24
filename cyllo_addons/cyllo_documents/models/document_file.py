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
import base64
import requests
import hashlib

from odoo import _, api, fields, models
from odoo.exceptions import UserError, AccessError


class DocumentFile(models.Model):
    """ Model used to store documents, perform document related functions """
    _name = 'document.file'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Documents'
    _order = "id desc"

    name = fields.Char(help="Document name", readonly=True)
    attachment = fields.Binary(string='File', help="Document data")
    date = fields.Datetime(help="Document create date")
    workspace_id = fields.Many2one('document.workspace', required=True,
                                   help="workspace name")
    user_id = fields.Many2one('res.users', string='Owner',
                              default=lambda self: self.env.user,
                              help="Document owner name, if the document  belongs to a specific partner")
    brochure_url = fields.Char(string="URL", help="Document sharable URL")
    extension = fields.Char(help="Document extension, helps to determine the file type", readonly=True)
    priority = fields.Selection([('0', 'None'), ('1', 'Favorite')], help="Favorite button")
    activity_ids = fields.One2many('mail.activity', string='Activities', help="List of activity ids")
    attachment_id = fields.Many2one('ir.attachment', ondelete='restrict', help="Attached item")
    content_url = fields.Char()
    content_type = fields.Selection(selection=[('file', 'File'), ('url', 'Url')], help="Document content type")
    preview = fields.Char(help="Preview URL")
    active = fields.Boolean(default=True, help="document is active or not")
    deleted_date = fields.Date(help="Document auto delete date")
    mimetype = fields.Char(string='Mime Type', help="Document mimetype")
    description = fields.Text(help="Write the description here")
    user_ids = fields.Many2many('res.users', help="Document related users")
    partner_id = fields.Many2one('res.partner', help="Document related")
    auto_delete = fields.Boolean(default=False, help="Document delete status")
    days = fields.Integer(help="auto delete in days")
    trash = fields.Boolean(help="To specify deleted items")
    delete_date = fields.Date(string='Date Delete', readonly=True)
    file_url = fields.Char(help="it store url while adding an url document")
    size = fields.Char(compute='_compute_size',
                       help='computed size of document')
    is_locked = fields.Boolean(string="Lock document",
                               help="To make document lock", default=False)
    document_file_id = fields.Many2one('document.file',
                                       help="Add document here")
    google_drive_file_key = fields.Char(string='Google Drive file id',
                                        help='id of file from google drive')
    one_drive_file_key = fields.Char(string='One Drive file id',
                                     help='id of file from one drive')
    is_crm_install = fields.Boolean(help="field to check crm installed or not")
    is_project_install = fields.Boolean(
        help="field to check project installed or not")
    document_tag_ids = fields.Many2many('document.tag', string='Tags')
    image_1920 = fields.Image(string='Preview Image',
                              help='Preview image of PDF')
    url_preview_image = fields.Image('URL Thumbnail Image',
                                     compute='_compute_url_preview_image',
                                     help='Preview image of URL')
    has_url_thumbnail = fields.Boolean()
    excel_thumbnail = fields.Image(help='Preview image of XLS')
    company_id = fields.Many2one('res.company', help='choose company',
                                 default=lambda self: self.env.company)
    request_document_id = fields.Many2one('request.document', string='Document Request',
                                          ondelete='set null', help='Associated document request')

    @api.depends('attachment_id')
    def _compute_size(self):
        """Function is used to fetch the file size of an attachment"""
        for rec in self:
            rec.size = str(rec.attachment_id.file_size / 1000) + ' Kb'

    @api.depends('preview')
    def _compute_url_preview_image(self):
        """Function is used to display the preview image"""
        for record in self:
            if record.preview:
                try:
                    response = requests.get(record.preview)
                    if response.status_code == 200:
                        image_data = response.content
                        base64_image = base64.b64encode(image_data).decode(
                            'utf-8')
                        record.url_preview_image = base64_image
                        record.has_url_thumbnail = True
                    else:
                        record.url_preview_image = False
                        record.has_url_thumbnail = False
                except Exception as e:
                    record.url_preview_image = False
                    record.has_url_thumbnail = False
            else:
                record.url_preview_image = False

    def unlink(self):
        if len(self.ids) > 1 and self.filtered(lambda rec: rec.is_locked):
            raise UserError(_("Can't group select locked items for deletion"))
        else:
            return super().unlink()

    @api.model
    def action_upload_document(self, *args):
        """Upload a document and add basic information about the file to the database.This function is used to
        upload a file and create a corresponding database record with basic information about the uploaded file,
        such as name, date, extension, and more.
        :param args: A tuple containing a dictionary with information about the uploaded file.
        :type args: Tuple,
        :return: document.file record"""
        attachment_id = self.env['ir.attachment'].sudo().create({
            'name': args[0]['file_name'],
            'datas': args[0]['file'],
            'res_model': 'document.file',
            'res_id': self.id,
            'public': True,
        })
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        doc_file = self.sudo().create({
            'attachment': attachment_id.datas,
            'workspace_id': args[0]['workspace_id'] if args[0]['workspace_id'] else 1,
            'name': args[0]['file_name'],
            'date': fields.Datetime.today().now(),
            'user_id': self.env.uid,
            'extension': args[0]['file_name'].split(".")[len(args[0]['file_name'].split(".")) - 1],
            'content_url': f"""{base_url}/web/content/{attachment_id.id}/{args[0]['file_name']}""",
            'mimetype': attachment_id.mimetype,
            'attachment_id': attachment_id.id,
            'brochure_url': str(base_url) + attachment_id.local_url,
            'google_drive_file_key': args[0].get('google_drive_file_key') if args[0].get(
                'google_drive_file_key') else False,
            'one_drive_file_key': args[0].get('one_drive_file_key') if args[0].get('one_drive_file_key') else False,
            'is_crm_install': True if self.env['ir.module.module'].sudo().search(
                [('name', '=', 'crm')]).state == 'installed' else False,
            'is_project_install': True if self.env['ir.module.module'].sudo().search(
                [('name', '=', 'project')]).state == 'installed' else False,
            'image_1920': args[0].get('preview_image') if args[0].get('preview_image') else False,
            'request_document_id': args[0].get('request_document_id', False),
            'company_id': args[0].get('company_id') or self.env.company.id,
        })
        return doc_file

    @api.model
    def action_btn_create_task(self, doc):
        """ Create a task based on a document if the 'project' module is installed. This function checks if the
        'project' module is installed and, if so, creates a task with the name of the document. It also associates
        the document's attachment with the task.
        :param doc: The document for which a task should be created.
        :type doc: recordset
        :return: act_window dict redirecting to created task form, False if 'project' module is not installed.
        :rtype: dict or bool"""
        module_id = self.env['ir.module.module'].sudo().search([('name', '=', 'project')])
        if module_id.state == 'installed':
            task = False
            for rec in self.browse(doc):
                task = self.env['project.task'].create({'name': rec['name']})
                rec.attachment_id.res_model = 'project.task'
                rec.attachment_id.res_id = task.id
            if task:
                return {
                    'type': 'ir.actions.act_window',
                    'name': _('Task'),
                    'res_model': 'project.task',
                    'res_id': task.id,
                    'view_mode': 'form',
                    'target': 'current',
                }
        return False

    @api.model
    def action_btn_create_lead(self, doc):
        """Create a CRM lead based on a document if the 'crm' module is installed. This function checks if the
        'crm' module is installed and, if so, creates a lead with the name of the document. It also associates the
        document's attachment with the lead.
        :param doc: The document for which a CRM lead should be created.
        :type doc: recordset
        :return: act_window dict redirecting to created lead form, False if 'crm' module is not installed.
        :rtype: dict or bool"""
        module_id = self.env['ir.module.module'].sudo().search([('name', '=', 'crm')])
        if module_id.state == 'installed':
            if not self.env.user.has_group('sales_team.group_sale_salesman'):
                raise AccessError(_("You do not have permission to create leads. Contact your Administrator"))
            lead = False
            for rec in self.browse(doc):
                lead = self.env['crm.lead'].create({'name': rec['name']})
                rec.attachment_id.res_model = 'crm.lead'
                rec.attachment_id.res_id = lead.id
            if lead:
                return {
                    'type': 'ir.actions.act_window',
                    'name': _('Lead'),
                    'res_model': 'crm.lead',
                    'res_id': lead.id,
                    'view_mode': 'form',
                    'target': 'current',
                }
        return False

    @api.model
    def download_zip_function(self, document_selected):
        """ Download selected documents as a ZIP archive. This function generates a URL to download the selected
        documents as a ZIP archive.
        :param document_selected: A list of document IDs to be included in the ZIP archive.
        :type document_selected: list
        :return: Action to open url a  for downloading the ZIP archive. """
        url = "/get/document?param=" + str(document_selected)
        return {'type': 'ir.actions.act_url', 'url': url, 'target': 'new'}

    @api.model
    def document_file_delete(self, doc_ids):
        """ Delete documents and move them to the document.trash. This function is responsible for deleting
        documents and creating corresponding records in the 'document.trash' table to keep track of the
        deleted documents.
        :param doc_ids: A list of document IDs to be deleted and moved to the trash.
        :type doc_ids: list
        :return: None """
        for docs in self.browse(doc_ids):
            self.env['document.trash'].create({
                'name': docs.name,
                'attachment': docs.attachment,
                'date': docs.date,
                'workspace_id': docs.workspace_id.id,
                'user_id': docs.user_id.id,
                'brochure_url': docs.brochure_url,
                'extension': docs.extension,
                'priority': docs.priority,
                'attachment_id': docs.attachment_id.id,
                'content_url': docs.content_url,
                'content_type': docs.content_type,
                'preview': docs.preview,
                'active': docs.active,
                'deleted_date': fields.Date.today(),
                'mimetype': docs.mimetype,
                'description': docs.description,
                'user_ids': docs.user_ids.ids,
                'partner_id': docs.partner_id,
                'days': docs.days,
                'file_url': docs.file_url,
                'doc_no': docs.id
            })
            docs.unlink()

    @api.model
    def document_file_archive(self, documents_selected):
        """ Archive documents and toggle their active status or delete date. This function is used to archive
        documents. Depending on the current state of the documents, it either toggles the 'active' status to mark
        them as archived or clears the 'delete_date' and sets them as active again.
        :param documents_selected: document ID to be archived.
        :type documents_selected: int
        :return: None """
        for docs in self.browse(documents_selected):
            if docs.active:
                docs.active = False
            elif docs.delete_date:
                docs.delete_date = False
                docs.active = True
            else:
                docs.active = True

    @api.model
    def on_mail_document(self, doc_ids):
        """ Open a new email compose window to send selected documents as attachments.This function opens a new
        email compose window with selected documents as attachments.The 'doc_ids' parameter contains a list of
        document IDs to be attached to the email.
        :param doc_ids: A list of document IDs to be attached to the email.
        :type doc_ids: list
        :return: Action to open a new email compose window."""
        default_composition_mode = self.env.context.get('default_composition_mode',
                                                        self.env.context.get('composition_mode', 'comment'))
        compose_ctx = dict(default_composition_mode=default_composition_mode, default_model='document.file',
                           default_res_ids=doc_ids, mail_tz=self.env.user.tz,
                           default_attachment_ids=self.browse(doc_ids).mapped('attachment_id').ids)
        return {
            'type': 'ir.actions.act_window',
            'name': 'Sent document',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(False, 'form')],
            'view_id': False,
            'target': 'new',
            'context': compose_ctx,
        }

    @api.model
    def delete_doc(self):
        """Delete documents from the trash based on the configured retention period.This function deletes documents
         from the 'document.trash' table based on the configured retention period specified in the
         'cyllo_documents.trash' parameter.It checks the 'deleted_date' of each document in the trash and
         deletes those that have reached or exceeded the retention period.
        :return: None """
        limit = self.env['ir.config_parameter'].sudo().get_param('cyllo_documents.trash')
        for rec in self.env['document.trash'].search([('deleted_date', '!=', False)]):
            delta = fields.Date.today() - rec.deleted_date
            if delta.days == limit:
                rec.unlink()

    @staticmethod
    def show_warning(message, info_type="info", sticky=False):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': message,
                'type': info_type,
                'sticky': sticky,
            }
        }

    def click_share(self):
        """Share a single document by generating a shareable URL or requesting a password for locked documents.
        This function allows users to share a single document. If the document is not locked,it generates a shareable
         URL using the 'document.share' model. If the document is locked, it opens a window to prompt the user to
         enter a password for access.
        :return: Shareable URL or action to enter a password."""
        document_id = self.env.context.get('document_id', False)
        if not self.browse(document_id).is_locked:
            return self.env['document.share'].create_url([document_id])
        else:
            return self.make_response('Please Enter Password', 'view_document_lock_share_form')

    def click_create_lead(self):
        """Create a CRM lead from the document's dropdown menu. This method allows users to create a CRM lead from
        a document if the document is not locked. If the document is locked, it prompts the user to enter a password.
        :return: Action to create a lead or a notification to install the CRM module.
        """
        document_id = self.env.context.get('document_id', False)
        if not self.browse(document_id).is_locked:
            result = self.action_btn_create_lead(document_id)
            if not result:
                return self.show_warning("Install CRM Module to use this function")
            return result
        else:
            return self.make_response('Please Enter Password', 'view_document_lock_lead_form')

    def click_create_task(self):
        """ Create a task from the document's dropdown menu. This method allows users to create a task from a
        document if the document is not locked. If the document is locked, it prompts the user to enter a password.
        :return: Action to create a task or a notification to install the Project module.
        """
        document_id = self.env.context.get('document_id', False)
        if not self.browse(document_id).is_locked:
            result = self.action_btn_create_task(document_id)
            if not result:
                return self.show_warning("Install Project Module to use this function")
            return result
        else:
            return self.make_response('Please Enter Password', 'view_document_lock_task_form')

    def click_create_mail(self):
        """Create an email from the document's dropdown menu. This method allows users to create an email from a
        document if the document is not locked. If the document is locked, it prompts the user to enter a password.
        :return: Action to create an email or a window to enter a password. """
        document_id = self.env.context.get('document_id', False)
        if not self.browse(document_id).is_locked:
            return self.on_mail_document([document_id])
        else:
            return self.make_response('Please Enter Password', 'view_document_lock_mail_form')

    def click_copy_move(self):
        """Copy or move a document from one workspace to another using the document's dropdown.His method allows
        users with appropriate permissions to copy or move a document from one workspace to another. It checks if
        the document is locked and if the user has the 'cyllo_documents.group_cyllo_documents_manager' group. If the user has
        permission and the document is not locked, it opens a window for copying the document. If the document is
        locked, it prompts the user to enter a password. If the user does not have  permission, it displays
        a notification.
        :return: Action to copy or move a document, or a notification for permission denied."""
        document_id = self.env.context.get('document_id', False)
        user_group = self.env.user.has_group('cyllo_documents.group_cyllo_documents_manager')
        if user_group:
            if not self.browse(document_id).is_locked:
                return self.make_response('Copy', False, 'work.space',
                                          {'default_doc_ids': [document_id]})
            else:
                return self.make_response('Please Enter Password', 'view_document_lock_copy_form')
        else:
            return self.show_warning("You don't have permission to perform this action", "danger")

    def click_document_archive(self):
        """Archive a document from the document's dropdown menu. This method allows users to archive a document if
        the document is not locked. If the document is locked, it prompts the user to enter a password.
        :return: None or action to enter a password."""
        document_id = self.env.context.get('document_id', False)
        if not self.browse(document_id).is_locked:
            self.document_file_archive(document_id)
        else:
            return self.make_response('Please Enter Password', 'view_document_lock_archive_form')

    def click_document_delete(self):
        """Delete a document from the document's dropdown menu. This method allows users to delete a document if
        they have the 'cyllo_documents.group_cyllo_documents_manager' group. It opens a window for users to choose between
        moving the document to the trash or permanently deleting it.
            :return: Action to choose between moving to trash or permanent deletion. """
        document_id = self.env.context.get('document_id', False)
        if document_id and self.browse(document_id).is_locked:
            return self.show_warning("Document is locked. Please unlock it before deletion.", "warning")

        user_group = self.env.user.has_group('cyllo_documents.group_cyllo_documents_manager')
        if user_group:
            return self.make_response('Choose One', 'view_document_delete_trash_form', 'document.delete.trash')

    def click_document_lock(self):
        """Lock a document from the document's dropdown menu. This method allows users to lock a document by opening
        a window where they can set a password for the document. Once locked, the document can only be accessed with
        the provided password.
        :return: Action to set a password and lock the document."""
        return self.make_response('Lock', 'view_document_lock_form')

    def get_doc_lock_record(self):
        document_id = self.env.context.get('document_id', False)
        doc_lock_id = self.env['document.lock'].search([('document_file_id', '=', document_id),
                                                        ('is_lock', '=', True)], order="id desc", limit=1)
        return doc_lock_id

    def make_response(self, name, view_name, res_model='document.lock', context=None):
        if context is None:
            context = {}
        document_id = self.env.context.get('document_id', False)
        doc_lock_id = self.get_doc_lock_record()
        response = {
            'type': 'ir.actions.act_window',
            'name': name,
            'res_model': res_model,
            'view_mode': 'form',
            'view_id': self.env.ref(f'cyllo_documents.{view_name}').id if view_name else False,
            'target': 'new',
        }
        if doc_lock_id:
            response["res_id"] = doc_lock_id.id
        else:
            response["context"] = context or {'default_document_file_id': document_id}
        return response

    def click_document_unlock(self):
        """ Unlock a document from the document's dropdown menu. This method allows users to unlock a locked
        document by opening a window where they can enter the document's password for access.
        :return: Action to enter the document's password and unlock it."""
        return self.make_response('Unlock', 'view_document_lock_unlock_form')

    def download_xlsx_record(self):
        module_name = 'cyllo_spreadsheet'
        module = self.env['ir.module.module'].sudo().search(
            [('name', '=', module_name), ('state', '=', 'installed')],
            limit=1
        )
        if not module:
            return self.show_warning("Install Spreadsheet Module to use this function")

    def click_download(self):
        """Download a document from the document's dropdown menu. This method allows users to download a document
        if it's not locked. If the document is locked, it prompts the user to enter a password before downloading.
        :return: Action to download the document or enter a password. """
        document_url = self.env.context.get('document_url', False)
        document_id = self.env.context.get('document_id', False)
        if not self.browse(document_id).is_locked:
            if self.extension == 'xlsx':
                return self.download_xlsx_record()
            else:
                return {
                    'type': 'ir.actions.act_url',
                    'url': document_url + '?download=true',
                }
        else:
            return self.make_response('Please Enter Password', 'view_document_lock_download_form')

    @api.model
    def get_document_count(self, *args):
        """Get the count of documents in a workspace and all documents. This method counts the number of documents
         in a specific workspace and the total number of documents across all workspaces.
           :param args: A list of arguments, with the first argument being the workspace ID.
           :type args: list
           :return: A tuple containing the count of documents in the specified workspace and the count of all documents.
           :rtype: tuple"""
        document_count_in_workspace = self.search_count([('workspace_id', '=', args[0])])
        all_document_count = self.sudo().search_count([])
        return document_count_in_workspace, all_document_count

    def validate_password(self, pwd):
        pwd = hashlib.sha256(pwd.encode()).hexdigest()
        ir_config = self.env['ir.config_parameter'].sudo()
        master_password = ir_config.get_param(
            'cyllo_documents.document_master_password', False)
        is_master_admin_only = ir_config.get_param(
            'cyllo_documents.document_master_password_admin_only')
        is_admin_user_group = self.env.user.has_group(
            'cyllo_documents.group_cyllo_documents_manager')
        if master_password:
            master_password = hashlib.sha256(
                master_password.encode()).hexdigest()
        if pwd == self.env['document.lock'].search([
            ('document_file_id', '=', self.id), ('is_lock', '=', True)],
                order="id desc", limit=1).password:
            return True
        if master_password and pwd == master_password:
            if not is_master_admin_only or is_admin_user_group:
                return True
        return False

    @api.returns('self')
    def copy_multi(self, default=None):
        if len(self.ids) > 1 and self.filtered(lambda rec: rec.is_locked):
            raise UserError(_("Can't group select locked items for duplication"))
        elif len(self.ids) == 1 and self.is_locked:
            action = self.make_response('Please Enter Password', 'view_document_lock_copy_form')
            action["views"] = [[False, "form"]]
            channel = "bus_do_action"
            message = {
                "channel": channel,
                "auth": {
                    "user": self.env.user.id
                },
                "action": action
            }
            self.env['bus.bus']._sendone(channel, "notification", message)
            return self
        else:
            return super().copy_multi(default)
