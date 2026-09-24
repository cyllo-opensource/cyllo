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
from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class AuditRule(models.Model):
    _name = 'audit.rule'
    _description = 'Audit Rule'
    _order = 'sequence, name'

    @api.model
    def _default_sequence(self):
        """Compute the next sequence value for a newly created audit rule."""
        last_sequence_rule = self.search([], order='sequence desc', limit=1)
        return (last_sequence_rule.sequence + 10) if last_sequence_rule else 10

    name = fields.Char(string='Rule Name', required=True,
                       help='Human-readable name of the audit rule.')
    sequence = fields.Integer(string='Sequence', default=_default_sequence,
                              help='Ordering priority used when evaluating rules.')
    active = fields.Boolean(string='Active', default=True,
                            help='Enable or disable this rule without deleting it.')
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company,
                                 help='Company that owns this audit rule.')
    model_id = fields.Many2one('ir.model', string='Model', required=True,
                               domain=[('transient', '=', False)],
                               ondelete='cascade', help='Select the model to audit')
    model_name = fields.Char(string='Model Name', related='model_id.model', store=True,
                             help='Technical model name derived from the selected model.')
    log_level = fields.Selection(
        [('info', 'Info'), ('warning', 'Warning'), ('critical', 'Critical')],
        string='Log Level', default='info', required=True,
        help='Severity level assigned to logs created by this rule.')
    # Operation Types
    track_create = fields.Boolean(string='Track Create', default=True,
                                  help='Log record creation operations.')
    track_write = fields.Boolean(string='Track Update', default=True,
                                 help='Log record update operations.')
    track_unlink = fields.Boolean(string='Track Delete', default=True,
                                  help='Log record deletion operations.')
    track_read = fields.Boolean(string='Track Read', default=False,
                                help="Warning: Enabling read tracking can generate a large number of logs")
    # Field Tracking
    tracking_scope = fields.Selection([('all', 'All Fields'), ('tracked', 'Only Tracked Fields'),
                                       ('excluded', 'All Except Excluded')],
                                      string='Tracking Scope', default='all',
                                      required=True,
                                      help='Select how field-level tracking is applied.')
    tracked_field_ids = fields.Many2many('ir.model.fields', 'audit_rule_tracked_field_rel',
                                         'rule_id', 'field_id', string='Tracked Fields',
                                         domain="[('model_id', '=', model_id)]",
                                         help='Fields to track when scope is set to "Only Tracked Fields".')
    excluded_field_ids = fields.Many2many('ir.model.fields', 'audit_rule_excluded_field_rel',
                                          'rule_id', 'field_id', string='Excluded Fields',
                                          domain="[('model_id', '=', model_id)]",
                                          help='Fields to exclude when scope is set to "All Except Excluded".')
    # User Tracking Selection - NEW ENHANCED FIELD
    user_selection_type = fields.Selection([('all', 'All Users'), ('specific', 'Specific Users'),
                                            ('exclude', 'Exclude Specific Users'),
                                            ('group', 'Users by Group')],
                                           string='User Selection', default='all', required=True,
                                           help='Choose which users are included in audit tracking.')
    # User IDs for specific tracking
    user_ids = fields.Many2many('res.users', 'audit_rule_user_rel', 'rule_id', 'user_id',
                                string='Users', help='Select specific users to track or exclude')
    # Group selection for group-based tracking
    group_ids = fields.Many2many('res.groups', 'audit_rule_group_rel', 'rule_id',
                                 'group_id', string='User Groups',
                                 help='Select groups whose members should be tracked')
    # User domain filter (advanced)
    user_domain = fields.Char(string='User Domain',
                              help='Advanced domain filter for users (e.g., [("company_id", "=", 1)])')
    # Additional Options
    track_ip = fields.Boolean(string='Track IP Address', default=True,
                              help='Capture client IP address in audit logs.')
    track_session = fields.Boolean(string='Track Session', default=False,
                                   help='Link logs to an audit session when available.')
    # Retention Policy
    has_retention = fields.Boolean(string='Enable Retention Policy', default=False,
                                   help='Automatically remove old logs for this model.')
    retention_days = fields.Integer(string='Keep Logs for (Days)', default=30,
                                    help='Number of days to retain logs when retention is enabled.')
    # Statistics
    log_count = fields.Integer(string='Log Count', compute='_compute_log_count',
                               help='Total number of audit logs matching this rule model.')
    notes = fields.Text(string='Notes',
                        help='Internal notes or operational comments for this rule.')
    user_count = fields.Integer(string='Affected Users', compute='_compute_user_count', store=True,
                                help='Number of users currently included by this rule.')

    @api.depends('model_id')
    def _compute_log_count(self):
        """Compute the number of logs related to this specific rule."""
        for audit_rule in self:
            audit_rule.log_count = self.env['audit.log'].search_count(
                [('rule_id', '=', audit_rule.id)])

    @api.onchange('tracking_scope')
    def _onchange_tracking_scope(self):
        """Reset incompatible field lists when tracking scope is changed."""
        if self.tracking_scope == 'all':
            self.tracked_field_ids = [(5, 0, 0)]
            self.excluded_field_ids = [(5, 0, 0)]
        elif self.tracking_scope == 'tracked':
            self.excluded_field_ids = [(5, 0, 0)]
        elif self.tracking_scope == 'excluded':
            self.tracked_field_ids = [(5, 0, 0)]

    @api.constrains('tracked_field_ids', 'excluded_field_ids')
    def _check_fields(self):
        """Ensure tracked and excluded field sets are not used together."""
        for audit_rule in self:
            if audit_rule.tracked_field_ids and audit_rule.excluded_field_ids:
                raise models.ValidationError(
                    'You cannot set both Tracked Fields and Excluded Fields. '
                    'Please choose one scope.')

    def _get_tracked_users(self):
        """Get the list of users that should be tracked concisely."""
        self.ensure_one()
        from odoo.tools.safe_eval import safe_eval

        user_filters = [('share', '=', False)]
        if self.user_selection_type == 'specific':
            return self.user_ids
        elif self.user_selection_type == 'exclude':
            return self.env['res.users'].search(user_filters) - self.user_ids
        elif self.user_selection_type == 'group':
            return self.group_ids.mapped('users').filtered(lambda group_user: not group_user.share)

        if self.user_domain and self.user_domain != '[]':
            try:
                user_filters += safe_eval(self.user_domain)
            except Exception:
                pass
        return self.env['res.users'].search(user_filters)

    def _should_track_user(self, user):
        """Check if a specific user should be tracked including domain check."""
        self.ensure_one()
        current_user_id = user.id
        if current_user_id == 1: return False  # Never track OdooBot/Superuser unless specifically needed

        # User Selection Check
        user_matches_selection = True
        if self.user_selection_type == 'specific':
            user_matches_selection = current_user_id in self.user_ids.ids
        elif self.user_selection_type == 'exclude':
            user_matches_selection = current_user_id not in self.user_ids.ids
        elif self.user_selection_type == 'group':
            user_matches_selection = any(
                current_user_id in user_group.users.ids for user_group in self.group_ids)

        if not user_matches_selection: return False

        # Domain Check
        if self.user_domain and self.user_domain != '[]':
            from odoo.tools.safe_eval import safe_eval
            try:
                evaluated_user_domain = safe_eval(self.user_domain)
                return current_user_id in self.env['res.users'].search(evaluated_user_domain).ids
            except Exception:
                return False  # Default to not tracking if domain is broken

        return True

    @api.depends('user_selection_type', 'user_ids', 'group_ids', 'user_domain')
    def _compute_user_count(self):
        """Compute the number of users affected by this rule accurately."""
        for audit_rule in self:
            audit_rule.user_count = len(audit_rule._get_tracked_users())

    def action_cleanup_logs(self):
        """Manually clean up ALL audit logs linked to this rule."""
        self.ensure_one()
        audit_logs = self.env['audit.log'].sudo().search([('rule_id', '=', self.id)])
        removed_log_count = len(audit_logs)
        if audit_logs:
            audit_logs.unlink()
            _logger.info("Audit Manual Cleanup: Removed %d log(s) for rule '%s'.",
                         removed_log_count, self.name)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Cleanup Complete',
                'message': f"Successfully removed {removed_log_count} log(s) for rule '{self.name}'.",
                'type': 'success',
                'sticky': False,
            },
        }

    @api.model
    def _cron_audit_log_retention(self):
        """Scheduled action to clean up expired logs based on per-rule settings."""
        rules = self.search([('has_retention', '=', True), ('retention_days', '>', 0)])
        for audit_rule in rules:
            retention_limit_date = fields.Datetime.subtract(fields.Datetime.now(),
                                                            days=audit_rule.retention_days)
            expired_audit_logs = self.env['audit.log'].sudo().search([
                ('rule_id', '=', audit_rule.id),
                ('create_date', '<', retention_limit_date)])
            if expired_audit_logs:
                _logger.info("Audit: Cleaned up %d expired logs for rule %s",
                             len(expired_audit_logs), audit_rule.name)
                expired_audit_logs.unlink()
