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
    'name': 'Cyllo POS Restaurant Appointment',
    'category': 'Sales/Point of Sale',
    'summary': 'Manage online table reservations in the POS restaurant floor screen using Cyllo Appointments',
    'description': """
        This bridge module integrates pos_restaurant with cyllo_appointment so that
        restaurant tables become bookable as appointment resources. Reservations
        created in cyllo_appointment appear live on the POS floor plan.
    """,
    'version': "1.0",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': [
        'pos_restaurant',
        'cyllo_appointment',
    ],
    'data': [
        'security/appointment_restaurant_security.xml',
        'data/appointment_type_data.xml',
        'views/pos_restaurant_views.xml',
        'views/appointment_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'cyllo_appointment_restaurant/static/src/app/**/*',
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': True,
    'post_init_hook': '_cyllo_appointment_restaurant_after_init',
}
