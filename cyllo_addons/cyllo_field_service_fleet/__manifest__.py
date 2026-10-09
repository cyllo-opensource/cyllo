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
{
    'name': 'Cyllo Fleet In Field Service',
    'category': 'Sales',
    'summary': "Integrate Fleet Management into Field Service for streamlined operations",
    'description': "This module integrates Fleet Management functionalities into Field Service, allowing for seamless"
                   " management of  vehicles, maintenance schedules, and assignments within your Field Service "
                   "operations. It enhances efficiency by providing a holistic view of your fleet and service requests,"
                   " enabling better decision-making and resource allocation. Streamline your operations and improve"
                   " overall productivity with Fleet In Field Service.",
    'version': "1.0",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['cyllo_field_service', 'fleet'],
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'views/field_service_request_views.xml',
        'views/field_service_request_form_templates.xml',
        'views/field_service_fleet_menus.xml',
        'views/fleet_vehicle_log_contract_views.xml',
        'reports/field_service_reports_templates.xml',
        'wizards/odometer_reading_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
