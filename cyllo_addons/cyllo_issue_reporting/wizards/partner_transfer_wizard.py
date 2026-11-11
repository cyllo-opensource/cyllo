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
import mimetypes
import logging
import requests
from odoo.exceptions import UserError
from markupsafe import Markup, escape

_logger = logging.getLogger(__name__)

DEFAULT_API_ENDPOINT = "https://accounts.cyllo.com/api/v1/cyllo_ticket"

class PartnerWizard(models.TransientModel):
    _name = 'partner.transfer.wizard'
    _description = 'Error Report Wizard to partner'

    name = fields.Char(string='Error Name / Exception', readonly=True)
    error_type = fields.Selection([
        ('backend', 'Python / Backend'),
        ('frontend', 'JavaScript / Frontend'),
        ('xml', 'XML / View / Data'),
        ('warning', 'User Warning / Validation'),
    ], string='Error Type', readonly=True, default='backend')
    issue_ref = fields.Char(readonly=True)
    issue_report_id = fields.Many2one('issue.report', string='Issue')
    module_name = fields.Char(string='Originating Module', readonly=True)
    file_location = fields.Char(string='File / Line', readonly=True)
    error_message = fields.Text(string='Error Message', readonly=True)
    traceback = fields.Text(string='Full Traceback', readonly=True)
    url = fields.Char(string='Page URL', readonly=True)
    user_id = fields.Many2one('res.users', string='Reported By',readonly=True)
    user_notes = fields.Text(string='User Feedback',readonly=True)
    admin_notes = fields.Text(string='Admin Feedback')
    attachment = fields.Binary(string='Attachment / Screenshot', attachment=True)
    attachment_filename = fields.Char(string="Filename")
    category_label=fields.Selection([
        ('technical','Technical issue'),
        ('billing','Billing & subscription'),
        ('accounts','Account & access'),
        ('feature','Feature request'),
        ('other','Other'),
    ],required=True, default='technical')

    @api.model
    def default_get(self, fields_list):
        """Function for extracting the attachment file from an issue report """
        res = super(PartnerWizard, self).default_get(fields_list)
        issue_id = res.get('issue_report_id') or self.env.context.get('default_issue_report_id')

        # 1. Fetch user attachment from the issue report if not already provided
        if issue_id and not res.get('attachment'):
            # Find the latest attachment linked to the issue.report record
            existing_attachment = self.env['ir.attachment'].sudo().search([
                ('res_model', '=', 'issue.report'),
                ('res_id', '=', issue_id),
            ], order='id desc', limit=1)
            if existing_attachment:
                res['attachment'] = existing_attachment.datas
                res['attachment_filename'] = existing_attachment.name
        return res



    def _generate_sentence_description(self):
        """Formats the wizard field values into a clear, readable narrative."""
        self.ensure_one()
        category_label = dict(self._fields['error_type'].selection).get(
            self.error_type, self.error_type or 'General'
        )
        sentences = []
        # 1. Overview sentence
        ref_text = f"under reference '{self.issue_ref}'" if self.issue_ref else ""
        sentences.append(
            f"An error {ref_text} categorized under '{category_label}' was logged in the system."
        )
        # 2. Location sentence
        if self.module_name and self.file_location:
            sentences.append(
                f"The failure was traced to module '{self.module_name}' at location '{self.file_location}'."
            )
        elif self.module_name:
            sentences.append(f"The failure originated from module '{self.module_name}'.")
        # 3. Context URL sentence
        if self.url:
            sentences.append(f"The incident occurred while accessing the page '{self.url}'.")
        # 4. User reporter sentence
        if self.user_id:
            user_desc = self.user_id.name
            if self.user_id.email:
                user_desc += f" ({self.user_id.email})"
            sentences.append(f"The issue was reported by user {user_desc}.")
        # 5. User feedback sentence
        if self.user_notes:
            sentences.append(f"User observation notes: \"{self.user_notes.strip()}\"")
        # 6. Admin transfer notes sentence
        if self.admin_notes:
            sentences.append(f"Administrator triage notes: \"{self.admin_notes.strip()}\"")
        narrative = " ".join(sentences)
        # 7. Append technical error & traceback sections
        sections = [narrative]
        if self.error_message:
            sections.append(f"--- ERROR MESSAGE ---\n{self.error_message.strip()}")

        return "\n\n".join(sections)
    def _prepare_attachments_payload(self):
        """Gathers Base64 encoded attachments with MIME types."""
        self.ensure_one()
        attachments = []
        # 1. Wizard's own uploaded attachment
        if self.attachment:
            filename = self.attachment_filename or f"screenshot_{self.issue_ref or 'issue'}.png"
            mime_type, _ = mimetypes.guess_type(filename)
            mime_type = mime_type or 'application/octet-stream'
            raw_data = self.attachment
            if isinstance(raw_data, bytes):
                raw_data = raw_data.decode('utf-8')
            attachments.append({
                'name': filename,
                'type': mime_type,
                'data': raw_data,
            })
        # 2. Attachments linked to parent issue report (avoiding duplicates)
        if self.issue_report_id:
            existing_attachments = self.env['ir.attachment'].sudo().search([
                ('res_model', '=', 'issue.report'),
                ('res_id', '=', self.issue_report_id.id),
            ])
            for att in existing_attachments:
                if self.attachment_filename and att.name == self.attachment_filename:
                    continue
                if att.datas:
                    att_data = att.datas.decode('utf-8') if isinstance(att.datas, bytes) else att.datas
                    attachments.append({
                        'name': att.name or f"attachment_{att.id}",
                        'type': att.mimetype or mimetypes.guess_type(att.name)[0] or 'application/octet-stream',
                        'data': att_data,
                    })
        return attachments
    def _prepare_api_payload(self):
        """Constructs the requested JSON payload structure."""
        self.ensure_one()
        category_name = dict(
            self._fields['category_label'].selection
        ).get(self.category_label, self.category_label or 'technical')

        return {
            'subject': f"[{self.issue_ref or 'ISSUE'}] {self.name or 'System Error'}",
            'description': self._generate_sentence_description(),
            'source': 'partner',
            'user_mail': self.env.user.email,
            'user_name':self.env.user.name,
            'category': category_name,
            'reference': self.issue_ref ,
            'attachments': self._prepare_attachments_payload(),

        }
    def action_send_report(self):
        """Submits the error report directly to the Partner Support API."""
        self.ensure_one()

        # 1. Duplicate Submission Check

        if self.issue_report_id and self.issue_report_id.state == 'transferred':
            raise UserError(_(
                "This issue (%s) has already been transferred to Partner Support."
            ) % (self.issue_ref or self.issue_report_id.name))

        # 2. Retrieve System Parameters directly (with fallback)

        icp = self.env['ir.config_parameter'].sudo()
        api_endpoint = (
            icp.get_param('cyllo_issue_reporting.api_endpoint') or DEFAULT_API_ENDPOINT
        ).strip()

        payload={
            "jsonrpc": "2.0",
            "method": "call",
            "params": self._prepare_api_payload()
        }

        try:

            response = requests.post(
                url=api_endpoint,
                json=payload,
                timeout=15,  # 15s timeout
            )
        except requests.exceptions.Timeout:
            _logger.error("Timeout reaching Partner API: %s", api_endpoint)
            raise UserError(_("The Partner Support API timed out after 15 seconds. Please try again later."))
        except requests.exceptions.ConnectionError:
            _logger.error("Connection failed for Partner API: %s", api_endpoint)
            raise UserError(_("Could not connect to Partner Support API. Please verify endpoint URL and network."))


        try:
            resp_json = response.json()

        except ValueError:
            _logger.error("Invalid JSON response from Partner API: %s", response.text[:400])
            raise UserError(_("Received an invalid response from the Partner Support API."))

        is_success = resp_json.get('result', {}).get('success') is True
        if is_success:
            remote_ref = resp_json.get('result', {}).get('ticket_id')
            ticket_url = resp_json.get('result', {}).get('redirect_url')
            # Store created ticket URL and update status to 'transfered'
            if self.issue_report_id:
                vals_to_write = {'state': 'transferred'}
                if ticket_url:
                    vals_to_write['ticket_url'] = ticket_url
                self.issue_report_id.write(vals_to_write)

            # Post formatted message to Chatter
            if self.issue_report_id:
                chatter_parts = [
                    _("Issue successfully transferred to Partner Support via API.")
                ]

                if remote_ref:
                    chatter_parts.append(
                        _("Partner Reference / Ticket: %s") % remote_ref
                    )

                if ticket_url:
                    chatter_parts.append(
                        Markup(
                            'Ticket URL: <a href="%s" target="_blank">%s</a>')
                        % (escape(ticket_url), escape(ticket_url))
                    )

                self.issue_report_id.message_post(
                    body=Markup("<br/>").join(
                        Markup("%s") % part if not isinstance(part,
                                                              Markup) else part
                        for part in chatter_parts
                    )
                )
            # Success notification with "View Ticket" button link
            links = []
            if ticket_url:
                links.append({
                    'label': _('View Ticket'),
                    'url': ticket_url,
                })
                notif_msg = _('The issue report has been successfully transferred to Partner Support. %s')
            else:
                notif_msg = _('The issue report has been successfully transferred to Partner Support.')
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Ticket Created Successfully'),
                    'message': notif_msg,
                    'type': 'success',
                    'sticky': True,  # Keep open so user can click "View Ticket"
                    'links': links,
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }
        else:

            error_message = resp_json.get('result', {}).get('error') or resp_json.get('message') or _(
                "Could not complete transfer to Partner Support."
            )
            login_url = resp_json.get('result', {}).get('redirect_url')
            # Store login URL on the record and wizard
            if login_url:
                if self.issue_report_id:
                    self.issue_report_id.write({'login_redirect_url': login_url})

            # Log failure in Chatter
            if self.issue_report_id:
                body = Markup("Partner Support Transfer Failed: %s") % escape(
                    error_message or ""
                )

                if login_url:
                    body += Markup(
                        '<br/>Login URL: <a href="%s" target="_blank">%s</a>'
                    ) % (
                                escape(login_url),
                                escape(login_url),
                            )

                self.issue_report_id.message_post(body=body)
            # Error notification with "Login to Support" button link
            links = []
            if login_url:
                links.append({
                    'label': _('Login to Support Portal'),
                    'url': login_url,
                })
                notif_msg = _('%(error)s %(link)s', error=error_message, link='%s')
            else:
                notif_msg = error_message
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Transfer Failed'),
                    'message': notif_msg,
                    'type': 'danger',
                    'sticky': True,  # Keep open so user can click "Login to Support Portal"
                    'links': links,
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }