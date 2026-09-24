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
    'name': 'Cyllo Front Desk - Appointment Integration',
    'category': 'Human Resources',
    'summary': """Bridge module to auto-create visitors from confirmed appointments and sync check-in/out with appointment state""",
    'description': """
        Cyllo Front Desk - Appointment Integration:
        - Automatically creates a Front Desk visitor when an appointment is confirmed
        - Visitor check-in pushes the linked appointment to In Progress
        - Visitor check-out marks the linked appointment as Done
        - Maps appointment partner, staff, and schedule to visitor fields
    """,
    'version': "1.0",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['cyllo_front_desk', 'cyllo_appointment'],
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'views/frontdesk_visitor_views.xml',
        'views/appointment_views.xml',
        'views/frontdesk_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
