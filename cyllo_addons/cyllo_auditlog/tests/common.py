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

from odoo.tests import common


class AuditLogCommon(common.TransactionCase):
    """Shared setup for audit log tests."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.AuditRule = cls.env['audit.rule']
        cls.AuditLog = cls.env['audit.log']
        cls.AuditLogLine = cls.env['audit.log.line']
        cls.AuditSession = cls.env['audit.session']
        cls.HttpRequest = cls.env['audit.http.request']
        cls.partner_model = cls.env['ir.model']._get('res.partner')
        cls.partner_name_field = cls.env['ir.model.fields'].search([
            ('model_id', '=', cls.partner_model.id),
            ('name', '=', 'name'),
        ], limit=1)
        cls.partner_email_field = cls.env['ir.model.fields'].search([
            ('model_id', '=', cls.partner_model.id),
            ('name', '=', 'email'),
        ], limit=1)

    def _create_rule(self, **values):
        vals = {
            'name': 'Test Audit Rule',
            'model_id': self.partner_model.id,
            'active': True,
            'track_create': True,
            'track_write': True,
            'track_unlink': True,
            'track_read': False,
            'tracking_scope': 'all',
            'user_selection_type': 'all',
        }
        vals.update(values)
        return self.AuditRule.create(vals)

    def _create_log(self, rule, **values):
        vals = {
            'user_id': self.env.user.id,
            'model_id': self.partner_model.id,
            'rule_id': rule.id,
            'res_id': values.pop('res_id', 1),
            'operation': values.pop('operation', 'write'),
            'log_level': values.pop('log_level', rule.log_level),
        }
        vals.update(values)
        return self.AuditLog.create(vals)

