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
from odoo import models, api, fields, _
from odoo.http import request
from odoo.tools import config
import logging
import json
from datetime import datetime

_logger = logging.getLogger(__name__)


class BaseAuditHook(models.AbstractModel):
    _inherit = 'base'

    def _get_audit_rules(self):
        """Get all active audit rules for this model with request-level caching."""
        # Fast bypass during module installation/uninstallation to prevent PostgreSQL crashes
        if not self.env.registry.ready: return []

        request_context = self._get_safe_request()
        if not request_context or getattr(request_context, 'audit_internal_call', False): return []

        # Optimization: Use request cache to avoid repeated searches in the same request
        if not hasattr(request_context, 'audit_rules_cache'): request_context.audit_rules_cache = {}
        if self._name in request_context.audit_rules_cache:
            return request_context.audit_rules_cache[self._name]

        # Critical: Only search if we aren't already searching (recursion guard)
        try:
            request_context.audit_internal_call = True
            rules = self.env['audit.rule'].sudo().search([
                ('model_id.model', '=', self._name),
                ('active', '=', True),
                '|', ('company_id', '=', False), ('company_id', '=', self.env.company.id)
            ])
            request_context.audit_rules_cache[self._name] = rules
            return rules
        finally:
            request_context.audit_internal_call = False

    def _get_safe_request(self):
        """Safely retrieve the request object and check if auditing should be active."""
        # Fast bypass during module installation or upgrades
        if config.get('init') or config.get('update'):
            return False

        try:
            # Check for request and verify it has a database (avoids background sync issues)
            if request and hasattr(request, 'db') and request.db:
                return request
        except (RuntimeError, AttributeError):
            pass
        return False

    def _should_track_user(self, rule):
        """Check if current user should be tracked"""
        return rule.sudo()._should_track_user(self.env.user)

    def _should_track_field(self, rule, field_name):
        """Check if a field should be tracked based on rule configuration"""
        scope = rule.tracking_scope
        if scope == 'all': return True
        tracked_or_excluded_fields = rule.sudo().tracked_field_ids if scope == 'tracked' else rule.sudo().excluded_field_ids
        return (field_name in tracked_or_excluded_fields.mapped('name')) == (scope == 'tracked')

    def _prepare_audit_log_vals(self, rule, operation, res_id, changes=None):
        """Prepare values for audit log creation"""
        vals = {
            'user_id': self.env.user.id,
            'company_id': rule.company_id.id or self.env.company.id,
            'model_id': rule.model_id.id,
            'rule_id': rule.id,
            'res_id': res_id,
            'operation': operation,
            'log_level': rule.log_level,
            'session_id': self._get_session_id() if rule.track_session else False,
            'ip_address': self._get_client_ip() if rule.track_ip else False,
            'http_request_id': self._get_http_request_id() if request else False,
        }

        if changes and operation == 'write':
            TECHNICAL = {'write_date', 'write_uid', 'needed_terms_dirty', 'message_has_error',
                         'message_main_attachment_id', 'tax_totals', 'invoice_payments_widget',
                         'invoice_outstanding_credits_debits_widget'}
            interesting_field_names = [field_name for field_name in changes if field_name not in TECHNICAL]
            primary_field_name = interesting_field_names[0] if len(interesting_field_names) == 1 else (
                "Multiple Fields" if interesting_field_names else list(changes.keys())[0])
            vals.update({
                'field_name': primary_field_name,
                'old_value': str(changes.get(primary_field_name, next(iter(changes.values())))['old']) or '',
                'new_value': str(changes.get(primary_field_name, next(iter(changes.values())))['new']) or '',
            })
        return vals

    def _create_audit_log(self, rule, operation, res_id, changes=None):
        """Create audit log entry with lines"""
        if operation == 'write' and not changes: return False
        try:
            log = self.env['audit.log'].sudo().create(
                self._prepare_audit_log_vals(rule.sudo(), operation, res_id, changes))
            if changes and operation == 'write':
                self.env['audit.log.line'].sudo().create([{
                    'log_id': log.id, 'field_name': changed_field_name,
                    'old_value': str(change_values['old']) if change_values['old'] is not None else '',
                    'new_value': str(change_values['new']) if change_values['new'] is not None else '',
                } for changed_field_name, change_values in changes.items()])
            return log
        except Exception:
            _logger.error("Failed to create audit log", exc_info=True)
            return False

    def _get_client_ip(self):
        """Get client IP address"""
        if not (request and hasattr(request, 'httprequest')): return ''
        request_environ = request.httprequest.environ
        return request_environ.get('HTTP_X_FORWARDED_FOR', '').split(',')[
            0].strip() or request.httprequest.remote_addr or ''

    def _get_session_id(self):
        """Get or create audit.session record for current request"""
        session = self.env['audit.session'].sudo().get_or_create_session()
        return session.id if session else False

    def _get_http_request_id(self):
        """Get or create an audit.http.request record for the current HTTP request"""
        request_context = self._get_safe_request()
        if not request_context or not hasattr(request_context, 'httprequest'):
            return False

        if hasattr(request_context, 'audit_http_request_id'):
            return request_context.audit_http_request_id

        # Create it via our HTTP request model
        path = request_context.httprequest.path
        url = request_context.httprequest.url
        method = request_context.httprequest.method

        http_request_log = self.env['audit.http.request'].sudo().log_request(
            path=path,
            url=url,
            method=method,
        )

        request_context.audit_http_request_id = http_request_log.id if http_request_log else False
        return request_context.audit_http_request_id

    def _get_x2many_changes_desc(self, rule, field_name, commands, sub_old_values=None):
        """Parse x2many commands with rule-based sub-field filtering."""
        if not commands: return ""
        related_model = self.env[self._fields[field_name].comodel_name].sudo()
        details = []
        for command in commands:
            if not isinstance(command, (list, tuple)): continue
            command_type, command_record_id = command[0], command[1]
            if command_type == 0:
                details.append(
                    f"New line: { {field_key: field_value for field_key, field_value in command[2].items() if field_key not in ['write_date', 'write_uid', 'id']} }")
            elif command_type == 1:
                field_differences = []
                for sub_field_name, new_sub_value in command[2].items():
                    if sub_field_name in ['write_date', 'write_uid', 'id'] or not self._should_track_field(rule,
                                                                                                           sub_field_name): continue
                    old_sub_value = (sub_old_values or {}).get(command_record_id, {}).get(sub_field_name) or \
                                    related_model.browse(command_record_id)[sub_field_name]
                    if str(old_sub_value) != str(new_sub_value):
                        field_differences.append(f"{sub_field_name}: {old_sub_value} -> {new_sub_value}")
                if field_differences: details.append(f"Line #{command_record_id} ({', '.join(field_differences)})")
            elif command_type == 2:
                details.append(f"Delete line #{command_record_id}")
        return f" | Details: {'; '.join(details)}" if details else ""

    @api.model_create_multi
    def create(self, vals_list):
        """Create records and log creation events for applicable audit rules."""
        records = super().create(vals_list)
        if self._name in ['audit.log', 'audit.rule', 'audit.log.line']: return records
        for rule in self._get_audit_rules():
            if rule.track_create and self._should_track_user(rule):
                for record in records: self._create_audit_log(rule, 'create', record.id)
        return records

    def write(self, vals):
        """Write records and log field-level changes for applicable audit rules."""
        if self._name in ['audit.log', 'audit.rule', 'audit.log.line']: return super().write(vals)
        rules = [
            audit_rule for audit_rule in self._get_audit_rules()
            if audit_rule.track_write and self._should_track_user(audit_rule)
        ]
        if not rules: return super().write(vals)

        SKIP = {
            'write_date', 'write_uid', '__last_update', 'message_ids', 'activity_ids',
            'message_follower_ids', 'message_has_error', 'message_main_attachment_id',
            'needed_terms_dirty', 'tax_totals', 'invoice_payments_widget',
            'invoice_outstanding_credits_debits_widget', 'is_move_sent'
        }
        tracked_fields = [field_name for field_name in vals if field_name not in SKIP] or []
        old_values_by_record, subrecord_old_values = {}, {}

        for rule in rules:
            for record in self:
                old_values_by_record.setdefault(record.id, {})
                for field_name in tracked_fields:
                    if self._should_track_field(rule, field_name) and field_name in self._fields:
                        current_value = record[field_name]
                        if self._fields[field_name].type == 'many2one':
                            old_values_by_record[record.id][field_name] = (
                                f"{current_value.display_name} (ID: {current_value.id})" if current_value else ""
                            )
                        elif self._fields[field_name].type in ['many2many', 'one2many']:
                            old_values_by_record[record.id][field_name] = (
                                f"{len(current_value)} records: {current_value.mapped('display_name')}"
                            )
                            for sub_command in (vals.get(field_name) or []):
                                if isinstance(sub_command, (list, tuple)) and sub_command[0] == 1:
                                    sub_record = self.env[self._fields[field_name].comodel_name].sudo().browse(
                                        sub_command[1])
                                    subrecord_old_values.setdefault(
                                        sub_command[1],
                                        {
                                            sub_field_name: sub_record[sub_field_name]
                                            for sub_field_name in sub_command[2]
                                            if sub_field_name in sub_record._fields
                                        }
                                    )
                        else:
                            old_values_by_record[record.id][field_name] = current_value

        result = super().write(vals)
        for rule in rules:
            for record in self:
                changes = {}
                for field_name, old_value in old_values_by_record.get(record.id, {}).items():
                    if not self._should_track_field(rule, field_name): continue  # Ensure per-rule filtering
                    new_value = record[field_name]
                    if self._fields[field_name].type == 'many2one':
                        new_display_value = f"{new_value.display_name} (ID: {new_value.id})" if new_value else ""
                        if old_value != new_display_value:
                            changes[field_name] = {'old': old_value, 'new': new_display_value}
                    elif self._fields[field_name].type in ['many2many', 'one2many']:
                        new_display_value = f"{len(new_value)} records: {new_value.mapped('display_name')}"
                        if old_value != new_display_value or field_name in vals:
                            changes[field_name] = {
                                'old': old_value,
                                'new': f"{new_display_value}{self._get_x2many_changes_desc(rule, field_name, vals.get(field_name), subrecord_old_values)}"
                            }
                    elif str(old_value) != str(new_value):
                        changes[field_name] = {'old': old_value, 'new': new_value}
                if changes: self._create_audit_log(rule, 'write', record.id, changes)
        return result

    def unlink(self):
        """Delete records and log unlink events for applicable audit rules."""
        if self._name in ['audit.log', 'audit.rule', 'audit.log.line']: return super().unlink()
        rules = [
            audit_rule for audit_rule in self._get_audit_rules()
            if audit_rule.track_unlink and self._should_track_user(audit_rule)
        ]
        for rule in rules:
            for record in self: self._create_audit_log(rule, 'unlink', record.id)
        return super().unlink()

    def _log_read_action(self, res_ids):
        """Internal helper to log read actions once per request/record."""
        request_context = self._get_safe_request()
        if not request_context or not res_ids or getattr(request_context, 'audit_internal_call', False): return

        # More aggressive system exclusion to handle upgrades smoothly
        SYSTEM_MODELS = {
            'audit.log', 'audit.rule', 'audit.log.line', 'bus.bus',
            'ir.module.module', 'ir.model', 'ir.model.fields', 'ir.ui.view',
            'ir.actions.report', 'ir.attachment', 'res.users.log', 'ir.http'
        }
        if self._name in SYSTEM_MODELS or self._name.startswith('ir.'): return

        rules = [
            audit_rule for audit_rule in self._get_audit_rules()
            if audit_rule.track_read and self._should_track_user(audit_rule)
        ]
        if not rules: return

        # Use request cache instead of recordset attribute
        if not hasattr(request_context, 'audit_read_logged'):
            request_context.audit_read_logged = set()

        for rule in rules:
            for record_id in res_ids:
                read_log_key = (rule.id, self._name, record_id)
                if read_log_key not in request_context.audit_read_logged:
                    self._create_audit_log(rule, 'read', record_id)
                    request_context.audit_read_logged.add(read_log_key)

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None, **read_kwargs):
        """Override search_read to log read actions on the results."""
        # FIX: Check if we're already in a read logging operation using request cache
        request_context = self._get_safe_request()
        if request_context and getattr(request_context, 'audit_skip_read', False):
            return super().search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order,
                                       **read_kwargs)

        res = super().search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order, **read_kwargs)

        # Only log if we have results and we're not in an internal call
        if res and request_context:
            try:
                # Set flag in request to prevent recursion
                request_context.audit_skip_read = True
                # Extract IDs from results
                res_ids = [search_result['id'] for search_result in res if search_result.get('id')]
                if res_ids:
                    self._log_read_action(res_ids)
            finally:
                if request_context:
                    request_context.audit_skip_read = False

        return res

    def web_read(self, specification):
        """Override web_read to log read actions."""
        # FIX: Check if we're already in a read logging operation using request cache
        request_context = self._get_safe_request()
        if request_context and getattr(request_context, 'audit_skip_read', False):
            return super().web_read(specification)

        # Get the records first
        records = self
        res = super().web_read(specification)

        # Only log if we have records and we're not in an internal call
        if records and request_context:
            try:
                request_context.audit_skip_read = True
                self._log_read_action(records.ids)
            finally:
                if request_context:
                    request_context.audit_skip_read = False

        return res

    def read(self, fields=None, load='_classic_read'):
        """Override read to log read actions."""
        # FIX: Check if we're already in a read logging operation using request cache
        request_context = self._get_safe_request()
        if request_context and getattr(request_context, 'audit_skip_read', False):
            return super().read(fields=fields, load=load)

        res = super().read(fields=fields, load=load)

        # Only log if we have records and we're not in an internal call
        if self and request_context:
            try:
                request_context.audit_skip_read = True
                self._log_read_action(self.ids)
            finally:
                if request_context:
                    request_context.audit_skip_read = False

        return res

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """Override name_search to log read actions on found records."""
        # FIX: Check if we're already in a read logging operation using request cache
        request_context = self._get_safe_request()
        if request_context and getattr(request_context, 'audit_skip_read', False):
            return super().name_search(name=name, args=args, operator=operator, limit=limit)

        res = super().name_search(name=name, args=args, operator=operator, limit=limit)

        # Only log if we have results and we're not in an internal call
        if res and request_context:
            try:
                request_context.audit_skip_read = True
                # Extract IDs from name_search results [(id, name), ...]
                res_ids = [search_result[0] for search_result in res if search_result and search_result[0]]
                if res_ids:
                    self._log_read_action(res_ids)
            finally:
                if request_context:
                    request_context.audit_skip_read = False

        return res
