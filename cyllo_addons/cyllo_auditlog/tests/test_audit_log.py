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

from psycopg2 import IntegrityError

from odoo.tools import mute_logger
from odoo.tests import tagged

from .common import AuditLogCommon


@tagged('post_install', '-at_install')
class TestAuditLog(AuditLogCommon):
    """Tests for audit log, line, session, and HTTP request records."""

    def test_01_audit_log_computes_display_and_record_name(self):
        rule = self._create_rule(name='Display Rule')
        partner = self.env['res.partner'].create({'name': 'Audit Display Partner'})

        log = self._create_log(rule, res_id=partner.id, operation='create')

        self.assertIn(self.env.user.name, log.display_name)
        self.assertIn('create', log.display_name)
        self.assertEqual(log.record_name, partner.display_name)

    def test_02_missing_target_record_uses_fallback_record_name(self):
        rule = self._create_rule(name='Missing Record Rule')

        log = self._create_log(rule, res_id=999999)

        self.assertEqual(log.record_name, '#999999')

    def test_03_audit_log_line_uses_model_field_label(self):
        rule = self._create_rule(name='Line Label Rule')
        log = self._create_log(rule, res_id=20)
        line = self.AuditLogLine.create({
            'log_id': log.id,
            'field_name': 'name',
            'old_value': 'Old',
            'new_value': 'New',
        })

        self.assertEqual(line.field_label, self.partner_name_field.field_description)

    def test_04_audit_session_computes_active_state_and_log_count(self):
        rule = self._create_rule(name='Session Rule')
        session = self.AuditSession.create({
            'name': 'audit-test-session',
            'user_id': self.env.user.id,
            'ip_address': '127.0.0.1',
        })

        self._create_log(rule, res_id=21, session_id=session.id)

        self.assertTrue(session.is_active)
        self.assertEqual(session.log_count, 1)

        session.write({'logout_time': '2026-07-01 00:00:00'})
        session.invalidate_recordset(['is_active', 'logout_time'])
        self.assertFalse(session.is_active)

    def test_05_audit_session_get_or_create_reuses_sid(self):
        first_session = self.AuditSession.get_or_create_session('same-session-id')
        second_session = self.AuditSession.get_or_create_session('same-session-id')

        self.assertEqual(first_session, second_session)
        self.assertEqual(first_session.name, 'same-session-id')
        self.assertEqual(first_session.user_id, self.env.user)

    def test_06_audit_session_unique_constraint(self):
        self.AuditSession.create({
            'name': 'unique-session-id',
            'user_id': self.env.user.id,
        })

        with mute_logger('odoo.sql_db'), self.env.cr.savepoint(), self.assertRaises(IntegrityError):
            self.AuditSession.create({
                'name': 'unique-session-id',
                'user_id': self.env.user.id,
            })

    def test_07_http_request_log_stores_request_metadata(self):
        request_log = self.HttpRequest.log_request(
            path='/web/test/audit',
            url='http://localhost/web/test/audit',
            method='GET',
            request_data='{}',
            response_code=204,
        )

        self.assertEqual(request_log.path, '/web/test/audit')
        self.assertEqual(request_log.url, 'http://localhost/web/test/audit')
        self.assertEqual(request_log.method, 'GET')
        self.assertEqual(request_log.request_data, '{}')
        self.assertEqual(request_log.response_code, 204)
        self.assertEqual(request_log.user_id, self.env.user)
