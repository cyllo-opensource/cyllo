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
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal


class SignRequestPortal(CustomerPortal):
    """ Class to define the portal views """

    def _prepare_home_portal_values(self, counters):
        """ Retrieve the count of total number of sign request """
        vals = super()._prepare_home_portal_values(counters)
        if 'sign_request_count' in counters:
            sign_requester = request.env['sign.requester'].sudo().search(
                [('partner_id', '=', request.env.user.partner_id.id)]).request_id.ids
            vals['sign_request_count'] = len(set(sign_requester))
        return vals
