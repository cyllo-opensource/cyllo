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


class AuditlogHttpRequest(models.Model):
    _name = 'audit.http.request'
    _description = 'HTTP Request Log'
    _order = 'create_date desc'
    _rec_name = 'path'

    path = fields.Char(string='Path', readonly=True, required=True, help='Relative HTTP request path.')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company,
                                 help='Company that owns this HTTP request audit entry.')
    url = fields.Char(string='Full URL', readonly=True, help='Complete URL captured for the request.')
    method = fields.Char(string='HTTP Method', readonly=True, default='POST', help='HTTP verb used for the request.')
    user_id = fields.Many2one(
        'res.users', string='User', readonly=True, help='User associated with the HTTP request.',
        default=lambda self: self.env.user
    )
    session_id = fields.Many2one(
        'audit.session', string='Session', readonly=True, ondelete='set null',
        help='Audit session linked to this HTTP request.'
    )
    ip_address = fields.Char(string='IP Address', readonly=True, help='Client IP address for the request.')
    user_agent = fields.Text(string='User Agent', readonly=True, help='Browser or client user-agent header.')
    request_data = fields.Text(string='Request Data', readonly=True, help='Captured payload or request body.')
    response_code = fields.Integer(string='Response Code', readonly=True, help='HTTP response status code.')
    create_date = fields.Datetime(string='Created on', readonly=True,
                                  help='Timestamp when this request log was created.')
    log_ids = fields.One2many('audit.log', 'http_request_id', string='Logs', readonly=True,
                              help='Audit logs generated within this HTTP request.')

    @api.model
    def log_request(self, path, url=None, method='POST', request_data=None,
                    response_code=200, session=None):
        """Create an HTTP request log entry."""
        from odoo.http import request as http_request
        client_ip_address = ''
        client_user_agent = ''
        audit_session_record = None
        if http_request:
            client_ip_address = http_request.httprequest.remote_addr or ''
            if 'HTTP_X_FORWARDED_FOR' in http_request.httprequest.environ:
                client_ip_address = http_request.httprequest.environ[
                    'HTTP_X_FORWARDED_FOR'].split(',')[0].strip()
            client_user_agent = http_request.httprequest.environ.get('HTTP_USER_AGENT', '')
            if not session and hasattr(http_request, 'session'):
                session_identifier = getattr(http_request.session, 'sid', False)
                if session_identifier:
                    audit_session_record = self.env['audit.session'].sudo().search(
                        [('name', '=', session_identifier)], limit=1
                    )

        return self.sudo().create({
            'path': path,
            'url': url or path,
            'method': method,
            'user_id': self.env.uid,
            'session_id': audit_session_record.id if audit_session_record else False,
            'ip_address': client_ip_address,
            'user_agent': client_user_agent,
            'request_data': request_data,
            'response_code': response_code,
        })
