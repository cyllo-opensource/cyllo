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
{
    'name': 'Cyllo Front Desk',
    'category': 'Human Resources',
    'summary': """Manage reception desks, visitor check-ins, notifications, and refreshment requests""",
    'description': """
Cyllo Front Desk manages front desk operations:
- Setup Multiple Stations (Front Desks)
- Log and track visitors check-in and check-out
- Automatically notify hosts via Email and Discuss
- Manage refreshment configuration and notification for visitor requests
    """,
    'version': "1.0",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['hr', 'mail'],
    'icon': '/cyllo_front_desk/static/description/front-desk.svg',
    'data': [
        'security/frontdesk_security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',

        'wizard/frontdesk_emergency_wizard_views.xml',
        'wizard/frontdesk_visitor_enquiry_wizard_views.xml',
        'views/frontdesk_drink_views.xml',
        'views/frontdesk_frontdesk_views.xml',
        'views/frontdesk_visitor_views.xml',
        'views/frontdesk_enquiry_views.xml',
        'views/res_config_settings_views.xml',
        'views/frontdesk_emergency_views.xml',
        'views/frontdesk_menus.xml',
    ],
    'demo': [
        'demo/demo.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': True,
}
