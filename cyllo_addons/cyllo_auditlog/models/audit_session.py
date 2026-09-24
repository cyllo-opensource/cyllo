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
from psycopg2 import IntegrityError
import logging

_logger = logging.getLogger(__name__)


class AuditSession(models.Model):
    _name = 'audit.session'
    _description = 'User Audit Session'
    _order = 'login_time desc'

    _sql_constraints = [
        ('unique_session_user', 'unique(name, user_id)', 'A session for this user ID already exists!')
    ]

    name = fields.Char(string='Session ID', required=True, readonly=True,
                       help='Session identifier captured from the web session.')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company,
                                 help='Company of the session owner at session creation.')
    user_id = fields.Many2one('res.users', string='User', required=True, readonly=True,
                              help='User owning this audited session.')
    ip_address = fields.Char(string='IP Address', readonly=True,
                             help='Client IP address at login/session creation time.')
    user_agent = fields.Text(string='User Agent', readonly=True,
                             help='Browser or client user-agent captured for the session.')
    login_time = fields.Datetime(string='Login Time', default=fields.Datetime.now, readonly=True,
                                 help='Timestamp when the session was first logged.')
    logout_time = fields.Datetime(string='Logout Time', readonly=True,
                                  help='Timestamp when the session ended, if available.')
    is_active = fields.Boolean(string='Still Active?', compute='_compute_is_active',
                               help='Indicates whether the session is still open.')

    log_ids = fields.One2many('audit.log', 'session_id', string='Logs', help='Audit logs linked to this session.')
    log_count = fields.Integer(string='Logs', compute='_compute_log_count',
                               help='Number of audit logs linked to this session.')

    def _compute_is_active(self):
        """Mark sessions as active when no logout timestamp exists."""
        for audit_session in self:
            audit_session.is_active = not audit_session.logout_time

    def _compute_log_count(self):
        """Compute number of logs related to each session."""
        for audit_session in self:
            audit_session.log_count = len(audit_session.log_ids)

    @api.model
    def get_or_create_session(self, sid=None):
        """Get or create audit.session record concisely."""
        from odoo.http import request
        if not (sid := sid or (request and getattr(request.session, 'sid', False))):
            return False

        current_user = self.env.user
        if not current_user or current_user._is_public():
            return False

        # Fast path
        session_rec = self.sudo().search([('name', '=', sid), ('user_id', '=', current_user.id)], limit=1)
        if session_rec:
            return session_rec

        # Compact IP/UA extraction
        client_ip_address = request.httprequest.remote_addr if request else ''
        if request and 'HTTP_X_FORWARDED_FOR' in request.httprequest.environ:
            client_ip_address = request.httprequest.environ['HTTP_X_FORWARDED_FOR'].split(',')[0].strip()

        # Database-level Concurrency Protection (Savepoint + Integrity Error Catch)
        try:
            with self.env.cr.savepoint():
                return self.sudo().create({
                    'name': sid,
                    'user_id': current_user.id,
                    'ip_address': client_ip_address,
                    'user_agent': request.httprequest.environ.get('HTTP_USER_AGENT', '') if request else '',
                    'login_time': fields.Datetime.now(),
                })
        except IntegrityError:
            # Another concurrent request already inserted the exact same session ID & user.
            # The database threw a Unique Violation error. We catch it, Postgres rolls back our
            # tiny savepoint, and we safely fetch the record the OTHER request just made.
            _logger.debug(
                f"Caught IntegrityError for concurrent session creation on User ID {current_user.id}. Safely fetching existing.")
            return self.sudo().search([('name', '=', sid), ('user_id', '=', current_user.id)], limit=1)
