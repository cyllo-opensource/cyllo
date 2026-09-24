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
from odoo import api, fields, models


class HrEmployee(models.Model):
    """
    Inherited the hr.employee model to add Work From Home (WFH) capabilities,
    including fields for geographic coordinates, address details, and
    functions to geolocate the WFH address.
    """
    _inherit = 'hr.employee'

    work_from_home = fields.Boolean(string="Work From Home")
    home_latitude = fields.Float(string="Latitude",digits=(10, 7))
    home_longitude = fields.Float(string="Longitude",digits=(10, 7))
    home_range=fields.Float(string="Range")
    wfh_street = fields.Char(string="WFH Street",
                                 groups="hr.group_hr_user")
    wfh_city = fields.Char(string="WFH City", groups="hr.group_hr_user")
    wfh_state_id = fields.Many2one(
        "res.country.state", string="WFH State",
        domain="[('country_id', '=?', wfh_country_id)]",
        groups="hr.group_hr_user")
    wfh_zip = fields.Char(string="WFH Zip", groups="hr.group_hr_user")
    wfh_country_id = fields.Many2one("res.country",
                                         string="WFH Country",
                                         groups="hr.group_hr_user")

    @api.model
    def _geo_localize(self, street='', zip='', city='', state='', country=''):
        """
        Retrieves geographic coordinates (latitude and longitude)
        for a given address.

        Args:
            street (str): The street address.
            zip (str): The postal code.
            city (str): The city.
            state (str): The state name.
            country (str): The country name.

        Returns:
            tuple: A tuple containing latitude and longitude (float) if found,
                   otherwise None.
        """
        geo_obj = self.env['base.geocoder']
        search = geo_obj.geo_query_address(street=street, zip=zip, city=city,
                                           state=state, country=country)
        result = geo_obj.geo_find(search, force_country=country)
        if result is None:
            search = geo_obj.geo_query_address(city=city, state=state,
                                               country=country)
            result = geo_obj.geo_find(search, force_country=country)
        return result

    def geo_localize(self):
        """
        Updates the geographic coordinates (latitude and longitude)
        for the employee's WFH address using the _geo_localize method.

        Returns:
            bool: True if the operation is successful.
        """
        for wfh in self:
            result = self._geo_localize(wfh.wfh_street,
                                        wfh.wfh_zip,
                                        wfh.wfh_city,
                                        wfh.wfh_state_id.name,
                                        wfh.wfh_country_id.name)
            if result:
                wfh.write({
                    'home_latitude': result[0],
                    'home_longitude': result[1],
                })
        return True