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
    'name': 'Cyllo Subscription',
    'category': 'Sales/CRM',
    "summary": """Allows the users to create and sell subscription products.""",
    'description': """This module helps to introduce and sell subscription products.""",
    'version': "1.0",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['sale_management', 'portal'],
    'icon':'/cyllo_subscription/static/description/subscription.svg',
    'data': [
        'security/cyllo_subscription_security.xml',
        'security/ir.model.access.csv',
        'data/product_data.xml',
        'data/ir_cron_data.xml',
        'data/ir_sequence_data.xml',
        'data/ir_actions_server_data.xml',
        'data/subscription_renew_templates_data.xml',
        'data/subscription_closed_templates_data.xml',
        'data/invoice_mail_templates_data.xml',
        'reports/subscription_report_views.xml',
        'reports/subscription_report_template.xml',
        'reports/ir_actions_report.xml',
        'views/account_move_views.xml',
        'views/product_template_views.xml',
        'views/subscription_pricing.xml',
        'views/sale_order_views.xml',
        'views/time_based_pricing_views.xml',
        'views/sale_order_template_views.xml',
        'views/subscription_order_views.xml',
        'views/subscription_portal_views.xml',
        'views/subscription_order_close_reason_views.xml',
        'wizards/subscription_close_views.xml',
        'views/cyllo_subscription_menus.xml',
        'views/res_config_settings_views.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'cyllo_subscription/static/src/js/portal.js'
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': True,
}
