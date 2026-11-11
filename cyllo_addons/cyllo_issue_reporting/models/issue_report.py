# -*- coding: utf-8 -*-

#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cyllo(<https://www.cyllo.com>)
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

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class IssueReport(models.Model):
    _name = 'issue.report'
    _description = 'Issue / Error Report'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'priority desc, create_date desc'

    name = fields.Char(string='Error Name / Exception', required=True, tracking=True)
    error_type = fields.Selection([
        ('backend', 'Python / Backend'),
        ('frontend', 'JavaScript / Frontend'),
        ('xml', 'XML / View / Data'),
        ('warning', 'User Warning / Validation'),
    ], string='Error Type',default='backend')
    issue_ref = fields.Char(readonly=True, default=_("New"))
    module_name = fields.Char(string='Originating Module', tracking=True)
    file_location = fields.Char(string='File / Line Location', tracking=True)
    error_message = fields.Text(string='Error Message')
    traceback = fields.Text(string='Full Traceback')
    url = fields.Char(string='Page URL')
    user_id = fields.Many2one('res.users', string='Reported By', default=lambda self: self.env.user, tracking=True)
    user_notes = fields.Text(string='User Feedback')
    resolution_notes = fields.Text(string='Resolution / Admin Notes')
    assigned_to_id = fields.Many2one('res.users', string='Assigned Developer', tracking=True)
    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Normal'),
        ('2', 'High'),
        ('3', 'Critical'),
    ], string='Priority', default='1', tracking=True)
    state = fields.Selection([
        ('draft', 'New'),
        ('in_progress', 'In Progress'),
        ('transferred', 'Transferred'),
        ('resolved', 'Resolved'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True,
        group_expand=True)
    ticket_url = fields.Char(string='Ticket Url', readonly=True, copy=False)
    login_redirect_url = fields.Char(string='Login Redirect URL', readonly=True, copy=False)
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company,
        index=True)
    is_readonly=fields.Boolean(string='Is Readonly',default=False)
    is_manager = fields.Boolean(compute='_compute_is_manager')

    @api.depends_context('uid')
    def _compute_is_manager(self):
        is_manager = self.env.user.has_group(
            'cyllo_issue_reporting.group_error_reporting_manager')
        for rec in self:
            rec.is_manager = is_manager

    @api.model
    def web_read_group(self, domain, fields, groupby, limit=None, offset=0,
                       orderby=False, lazy=True):
        """Fold the 'cancelled' column by default in Kanban view"""
        result = super().web_read_group(
            domain, fields, groupby, limit=limit, offset=offset, orderby=orderby, lazy=lazy
        )
        if groupby and groupby[0].split(':')[0] == 'state':
            for group in result.get('groups', []):
                if group.get('state') == 'cancelled':
                    group['__fold'] = True
        return result


    @api.model_create_multi
    def create(self, vals_list):
        """Function for creating multiple issue reference number automatically"""
        for vals in vals_list:
            if vals.get('issue_ref', _("New")) == _("New"):
                vals['issue_ref'] = self.env['ir.sequence'].next_by_code('i_seq')
        records = super(IssueReport, self).create(vals_list)

        return records

    def action_set_in_progress(self):
        """Function for setting in_progress status of issue report."""
        self.write({'state': 'in_progress'})

    def action_set_resolved(self):
        """Function for setting resolved status of issue report."""
        self.write({'state': 'resolved'})
        
    def action_set_cancelled(self):
        """Function for setting cancelled status of issue report."""
        self.write({'state': 'cancelled'})

    def action_set_draft(self):
        """Function for setting draft status of issue report."""
        self.write({'state': 'draft'})

   
    def action_partner_transfer(self):
        """Function for calling the  partner transfer wizard and passess the data."""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Partner Transfer Wizard',
            'res_model': 'partner.transfer.wizard',
            'context': {
                'default_name': self.name,
                'default_error_type':self.error_type,
                'default_issue_ref':self.issue_ref,
                'default_module_name':self.module_name,
                'default_file_location':self.file_location,
                'default_error_message': self.error_message,
                'default_traceback': self.traceback,
                'default_url':self.url,
                'default_user_id':self.user_id.id,
                'default_user_notes':self.user_notes,
                'default_issue_report_id':self.id,
            },
            'view_mode': 'form',
            'target': 'new',
        }

    def action_ticket_redirect(self):
        """Redirects to the created ticket URL in Partner Support."""
        self.ensure_one()
        if not self.ticket_url:
            raise UserError(_("No ticket URL is available for this issue."))
        if not self.ticket_url.startswith(('http://', 'https://')):
            raise UserError(_("Invalid or unsafe ticket URL format."))
        return {
            'type': 'ir.actions.act_url',
            'url': self.ticket_url,
            'target': 'new',
        }
    
    def action_login_redirect(self):
        """Redirects user to the login/authentication URL returned by the API."""
        self.ensure_one()
        if not self.login_redirect_url:
            raise UserError(_("No login redirect URL is available for this issue."))
        if not self.login_redirect_url.startswith(('http://', 'https://')):
            raise UserError(_("Invalid or unsafe login URL format."))
        return {
            'type': 'ir.actions.act_url',
            'url': self.login_redirect_url,
            'target': 'new',
        }



