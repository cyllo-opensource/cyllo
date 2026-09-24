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


class RequestDocument(models.Model):
    """ module to store document requests """
    _name = 'request.document'
    _description = 'Request document from user'
    _rec_name = 'display_name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    display_name = fields.Char(help='display name document request', default=_('New'), copy=False)
    user_id = fields.Many2one('res.users', help="Choose User", required=True)
    requested_by_id = fields.Many2one('res.users', help="User who created request",
                                      string="Requested User", default=lambda self: self.env.user,
                                      readonly=True)
    needed_doc = fields.Text(string='Document Needed', required=True, help="Document needed by requestor")
    workspace_id = fields.Many2one('document.workspace', required=True,
                                   help="Select the workspace associated with this item.")
    manager_id = fields.Many2one('res.users', help="Select Manager")
    workspace = fields.Char(related='workspace_id.name', string='Workspace Name', help='Workspace name')
    reject_reason = fields.Text(string='Reason', help="Reason for rejection")
    state = fields.Selection(selection=[('draft', 'Draft'), ('requested', 'Requested'), ('accepted', 'Accepted'),
                                        ('rejected', 'Rejected')], default='draft',
                             help="Choose the current state of the item: Requested, Accepted, or Rejected.")
    company_id = fields.Many2one('res.company', string='Company', help='choose company',
                                 default=lambda self: self.env.company)
    document_file_ids = fields.One2many('document.file', 'request_document_id', string='Documents')
    document_count = fields.Integer(string='Document Count', compute='_compute_document_count')

    @api.depends('document_file_ids')
    def _compute_document_count(self):
        for rec in self:
            rec.document_count = len(rec.document_file_ids)

    def action_view_documents(self):
        """ Method to view uploaded document(s) for this request """
        self.ensure_one()
        action = {
            'name': _('Uploaded Documents'),
            'type': 'ir.actions.act_window',
            'res_model': 'document.file',
            'view_mode': 'kanban,tree,form',
            'domain': [('id', 'in', self.document_file_ids.ids)],
        }
        return action

    @api.model_create_multi
    def create(self, vals_list):
        """ Super the create function to generate sequences for document.request"""
        for vals in vals_list:
            if not vals.get('display_name') or vals['display_name'] == _('New'):
                vals['display_name'] = self.env['ir.sequence'].next_by_code('document.request') or _('New')
        return super().create(vals_list)

    def action_send_document_request(self):
        """ function to send document request through email """
        self.state = 'requested'
        user_id = self.env.user
        mail_content = f'Hello <br/> {user_id.name} Requested Document <br/>' \
                       f'{self.needed_doc}'
        main_content = {
            'subject': _('Document Request'),
            'body_html': mail_content,
            'email_to': self.user_id.partner_id.email,
        }
        self.env['mail.mail'].sudo().create(main_content).send()

    @api.model
    def get_request(self):
        """Function to fetch all requests for the currently logged-in user. This function retrieves all requests
        related to the current user from the 'request.document' model and formats the data into a list of
        dictionaries containing relevant information about each request.
        Returns:
            list of dict: A list of dictionaries containing information about the requests.
        """
        request_ids = self.env['request.document'].search([('user_id', '=', self.env.uid)])
        context = [{
            'request_id': rec.id,
            'user_id': rec.user_id.name,
            'manager_id': rec.manager_id.name,
            'needed_doc': rec.needed_doc,
            'workspace': rec.workspace,
            'workspace_id': rec.workspace_id.id,
        } for rec in request_ids]
        return context

    def open_wizard_view(self):
        """ Method is used to get the wizard view for requesting docs """
        view_id = self.env.ref('cyllo_documents.view_request_document_wizard_form').id
        return {
            'type': 'ir.actions.act_window',
            'name': 'Add Document Request',
            'res_model': 'request.document',
            'view_mode': 'form',
            'target': 'new',
            'views': [[view_id, "form"]]
        }