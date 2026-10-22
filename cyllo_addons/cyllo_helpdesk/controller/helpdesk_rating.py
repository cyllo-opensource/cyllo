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
from odoo import http
from odoo.http import request
from odoo.addons.rating.controllers.main import Rating as RatingController


class HelpdeskRatingController(RatingController):
    """Prevent a consumed helpdesk rating from being submitted again."""

    @http.route(
        '/rate/<string:token>/<int:rate>',
        type='http',
        auth='public',
        website=True,
    )
    def action_open_rating(self, token, rate, **kwargs):
        rating = request.env['rating.rating'].sudo().search(
            [('access_token', '=', token)],
            limit=1,
        )
        if rating and rating.res_model == 'helpdesk.ticket' and rating.consumed:
            return request.redirect('/rate/%s/submit_feedback' % token)

        return super().action_open_rating(token, rate, **kwargs)
