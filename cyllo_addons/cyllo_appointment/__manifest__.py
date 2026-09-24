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
    'name': 'Cyllo Appointments',
    'category': 'Services/Appointments',
    'summary': 'Advanced Appointment Scheduling with Resources, Staff, and Notifications',
    'description': """
        Cyllo Appointment - A comprehensive appointment scheduling solution.

        Features:
        - Appointment Types with configurable settings
        - Resource & Staff Management
        - Time Slot Management (intervals, working hours)
        - Email & WhatsApp Notifications and Reminders
        - Rescheduling support
        - Minimum booking notice
        - Confirmation and follow-up messages
        - User-friendly interface
    """,
    'version': "1.0",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'icon': '/cyllo_appointment/static/description/cyllo_appointment_tick.svg',
    'depends': [
        'portal',
        'mail',
        'calendar',
        'resource',
        'hr',
        'sms',
        'web',
        'website',
        'website_sale',
        'payment',
        'cyllo_whatsapp',
        'event',
        'cyllo_accounting',
    ],
    'data': [
        # Security
        'security/appointment_security.xml',
        'security/ir.model.access.csv',
        # Data
        'data/appointment_sequence.xml',
        'data/appointment_mail_templates.xml',
        # Views
        'views/appointment_type_views.xml',
        'views/appointment_resource_views.xml',
        'views/hr_employee_views.xml',
        'views/appointment_slot_views.xml',
        'views/appointment_views.xml',
        'views/appointment_settings_views.xml',
        'views/appointment_menus.xml',
        'views/website_appointment_templates.xml',
        'views/website_manage_templates.xml',
        'views/portal_templates.xml',
        'views/sale_order_views.xml',
        'views/event_event_views.xml',
        'views/appointment_refund_tier_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'cyllo_appointment/static/src/css/appointment_pro.css',
        ],
        'web.assets_frontend': [
            'cyllo_appointment/static/src/js/appointment_booking.js',
            'cyllo_appointment/static/src/js/appointment_reschedule.js',
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
    'application': True,
    'auto_install': False,
}
