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
    'name': "Cyllo Advance CRM Leads",
    'description': 'This module is used to create CRM leads for more options',
    'summary': 'Cyllo Crm Lead Creation',
    'version': "1.0",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['cyllo_base', 'crm', 'website_sale_wishlist', 'base_automation'],
    'data': [
        'data/ir_cron_data.xml',
        'data/mail_template.xml',
        'data/crm_setup_automated_action.xml',
        'views/base_automation_views.xml',
        'views/crm_lead_views.xml',
        'views/res_config_settings_views.xml',
        'views/referral_template.xml',
        'views/templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'cyllo_crm_advance_lead/static/src/js/website_sale_delay_referral_popup.js',
            'cyllo_crm_advance_lead/static/src/css/crm_lead_referral_template.css'
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': True,
    'application': False,
    'uninstall_hook': 'uninstall_hook',
}
