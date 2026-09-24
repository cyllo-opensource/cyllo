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
import math
from odoo import http


class GeoController(http.Controller):
    """
    A controller to check if geographic coordinates are within the allowable
    working range of an employee's work location (home or company).
    """
    @http.route('/check_geo_location', type='json', auth='user')
    def check_geo_location(self, **kwargs):
        """
        Checks if the provided coordinates are within the employee's allowable work range.

        Args:
            **kwargs: A dictionary containing:
                - data (dict):
                    - latitude (float): The latitude to check.
                    - longitude (float): The longitude to check.
                    - company (int): The ID of the user's company.
                    - userId (int): The ID of the current user.

        Returns:
            bool: True if the coordinates are within the allowable range, False otherwise.
        """
        data = kwargs.get('data', {})
        latitude = float(data.get('latitude', 0))
        longitude = float(data.get('longitude', 0))
        user_company = int(data.get('company'))
        user_id = int(data.get('userId'))
        employee_id = http.request.env['hr.employee'].search(
            [('user_id', '=', user_id), ('company_id', '=', user_company)])
        is_wfh = employee_id.work_from_home
        current_company = http.request.env['res.company'].browse(user_company)
        if is_wfh:
            work_latitude = employee_id.home_latitude
            work_longitude = employee_id.home_longitude
            work_range = employee_id.home_range if employee_id.home_range else current_company.range
        else:
            work_latitude = current_company.company_latitude
            work_longitude = current_company.company_longitude
            work_range = current_company.range
        R = 6378137.0
        phi1 = math.radians(work_latitude)
        phi2 = math.radians(latitude)
        delta_phi = math.radians(latitude - work_latitude)
        delta_lambda = math.radians(longitude - work_longitude)
        # Haversine formula
        a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(
            phi2) * math.sin(delta_lambda / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        distance = R * c
        return distance <= work_range
