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
from odoo import http, fields
from odoo.http import request
from odoo.addons.web.controllers.session import Session

class AuditSessionController(Session):
    @http.route('/web/session/logout', type='http', auth="none")
    def logout(self):
        if request and getattr(request, 'session', False):
            session_rec = request.env['audit.session'].sudo().search([('name', '=', request.session.sid)], limit=1)
            if session_rec:
                session_rec.sudo().write({'logout_time': fields.Datetime.now()})
        return super(AuditSessionController, self).logout()
