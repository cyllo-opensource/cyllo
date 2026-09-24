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


class FieldServiceRequestCount(CustomerPortal):
    """Extends CustomerPortal to display the count of field service requests
    for the current user."""

    def _prepare_home_portal_values(self, counters):
        """Prepare values for the home portal page."""
        vals = super()._prepare_home_portal_values(counters)
        if 'fs_req_count' in counters:
            vals['fs_req_count'] = request.env[
                'field.service.request'].sudo().search_count(
                [('partner_id', '=', request.env.user.partner_id.id)])
        return vals
