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
from odoo import models, fields, api
from odoo.http import request


class AuditLog(models.Model):
    _name = 'audit.log'
    _description = 'Audit Log'
    _order = 'create_date desc'

    display_name = fields.Char(string='Display Name', compute='_compute_display_name', store=True,
                               help='Computed label summarizing this audit entry.')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company,
                                 help='Company that owns this audit log entry.')
    user_id = fields.Many2one('res.users', string='User', required=True, default=lambda self: self.env.user,
                              readonly=True, help='User who triggered the audited action.')
    user_name = fields.Char(related='user_id.name', store=True, help='Cached user name for search and reporting.')
    model_id = fields.Many2one('ir.model', string='Model', required=True, readonly=True, ondelete='cascade',
                               help='Business model where the operation occurred.')
    model_name = fields.Char(related='model_id.name', store=True, help='Human-readable model name for this log.')
    model = fields.Char(related='model_id.model', store=True, help='Technical model identifier for this log.')
    res_id = fields.Integer(string='Record ID', required=True, readonly=True,
                            help='ID of the record affected by the operation.')
    record_name = fields.Char(string='Record Name', compute='_compute_record_name', store=True,
                              help='Display name of the audited record when available.')
    # FIX: Add 'read' to the selection options
    operation = fields.Selection([
        ('create', 'Create'),
        ('write', 'Update'),
        ('unlink', 'Delete'),
        ('read', 'Read')  # Added read operation
    ], string='Operation', required=True, readonly=True, help='Type of operation captured in this log.')
    field_name = fields.Char(readonly=True, help='Primary field highlighted for single-field updates.')
    old_value = fields.Text(readonly=True, help='Value before the change, when applicable.')
    new_value = fields.Text(readonly=True, help='Value after the change, when applicable.')
    line_ids = fields.One2many('audit.log.line', 'log_id', string='Change Lines',
                               help='Detailed per-field changes for update operations.')
    log_level = fields.Selection([('info', 'Info'), ('warning', 'Warning'), ('critical', 'Critical')],
                                 string='Log Level', required=True, readonly=True,
                                 help='Severity level inherited from the audit rule.')
    ip_address = fields.Char(readonly=True, help='Client IP address captured for the action.')
    rule_id = fields.Many2one('audit.rule', string='Audit Rule', readonly=True, ondelete='set null',
                              index=True, help='Audit rule that triggered this log entry.')
    session_id = fields.Many2one('audit.session', string='Audit Session', readonly=True,
                                 help='Audit session linked to this action.')
    http_request_id = fields.Many2one('audit.http.request', string='HTTP Request', readonly=True,
                                      help='HTTP request log entry associated with this action.')
    create_date = fields.Datetime(string='Change Date', default=fields.Datetime.now, readonly=True,
                                  help='Timestamp when the audit entry was created.')

    @api.depends('user_id', 'create_date', 'operation', 'model_id', 'res_id')
    def _compute_display_name(self):
        """Build a display label combining actor, operation, record, and timestamp."""
        for audit_log in self:
            audit_log.display_name = (
                f"{audit_log.user_id.name} - {audit_log.operation} - "
                f"{audit_log.model_id.name} #{audit_log.res_id} - {audit_log.create_date}"
            )

    @api.depends('model', 'res_id')
    def _compute_record_name(self):
        """Resolve a readable record name from the audited model and record id."""
        for audit_log in self:
            try:
                target_record = self.env[audit_log.model].sudo().browse(audit_log.res_id)
                audit_log.record_name = (
                    target_record.display_name if target_record.exists() else f"#{audit_log.res_id}"
                )
            except Exception:
                audit_log.record_name = f"#{audit_log.res_id}"


class AuditLogLine(models.Model):
    _name = 'audit.log.line'
    _description = 'Audit Log Line'
    _order = 'log_id, id'

    log_id = fields.Many2one('audit.log', required=True, ondelete='cascade', help='Parent audit log entry.')
    company_id = fields.Many2one('res.company', related='log_id.company_id', store=True, readonly=True,
                                 help='Company of the parent audit log.')
    field_name = fields.Char(required=True, help='Technical field name that changed.')
    field_label = fields.Char(compute='_compute_field_label', store=True,
                              help='User-friendly label for the changed field.')
    old_value = fields.Text(help='Field value before the change.')
    new_value = fields.Text(help='Field value after the change.')

    @api.depends('log_id.model_id', 'field_name')
    def _compute_field_label(self):
        """Compute a human-readable field label from model metadata."""
        for audit_log_line in self:
            audit_log_line.field_label = audit_log_line.field_name.replace('_', ' ').title()
            if audit_log_line.log_id.model_id:
                field_metadata = self.env['ir.model.fields'].search([
                    ('model_id', '=', audit_log_line.log_id.model_id.id),
                    ('name', '=', audit_log_line.field_name)
                ], limit=1)
                if field_metadata:
                    audit_log_line.field_label = field_metadata.field_description
