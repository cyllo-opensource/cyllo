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
    'name': 'Cyllo Zoom',
    'category': 'Extra tool',
    'summary': 'Meeting with cyllo',
    'description': """
        Cyllo zoom is a application to link with zoom in activity type.
        Zoom credentials are configured globally in Settings → General Settings
        → Zoom Integration and apply to all users.
    """,
    'version': "1.0",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['base_setup', 'cyllo_base', 'sale', 'crm', 'calendar'],
    'data': [
        'data/ir_cron_data.xml',
        'views/res_config_settings_view.xml',
        'views/mail_activity_schedule_form_view.xml',
        'views/calendar_event_views.xml',
        'views/calender_event_quick_form_view.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
