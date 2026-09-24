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
    'name': 'Cyllo Multiple SMS Gateway Integration',
    'category': 'Extra Tools',
    'summary': 'Module to send SMS through different SMS gateway',
    'description': "This modules helps to send SMS using different SMS gateways including "
                   "D7, Twilio, Vonage, TeleSign, MessageBird and Telnyx",
    'version': "1.0",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['cyllo_base', 'sale_management', 'website'],
    'data': [
        'security/multi_sms_gateway_groups.xml',
        'security/sms_history_security.xml',
        'security/ir.model.access.csv',
        'data/sms_gateway_data.xml',
        'views/sms_history_views.xml',
        'views/portal_share_views.xml',
        'views/sms_gateway_config_views.xml',
        'wizards/send_sms.xml',
        'views/multi_sms_gateway_menus.xml',
        'views/website_views.xml',
        'templates/login_templates.xml',
        'templates/verify_otp_templates.xml',
        'templates/web_login_templates.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'cyllo_sms_gateway/static/src/**/*',
        ]
    },
    'external_dependencies': {
        'python': ['twilio', 'clicksend_client', 'pycountry']},
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False
}
