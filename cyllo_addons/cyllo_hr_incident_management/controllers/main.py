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


class HrIncidentPortal(CustomerPortal):
    """ Class to define the 'hr.incident' portal view """

    def _prepare_home_portal_values(self, counters):
        """ Function to get the count of total number of tickets """
        vals = super()._prepare_home_portal_values(counters)
        if 'incident_count' in counters:
            vals['incident_count'] = request.env[
                'hr.incident'].sudo().search_count(
                [('incident_receptor_id', '=',
                  request.env.user.employee_ids.id)])
        return vals
