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
    'name': 'Cyllo Crm',
    'description': 'This module is used to add and remove features in crm module',
    'summary': 'Cyllo Crm Management',
    'version': "1.0",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['cyllo_base', 'crm', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'data/mail_template.xml',
        'data/crm_get_customer_local_time.xml',
        'wizard/crm_leads_to_change_views.xml',
        'views/res_config_settings_views.xml',
        'views/crm_stage_views.xml',
        'views/crm_lead_views.xml',
        'views/crm_dashboard_views.xml',
        'views/crm_subscription_report_views.xml',
        'views/crm_stage_activity_view.xml',
        'wizard/crm_leads_to_change_views.xml',
        'wizard/crm_stage_exit_criteria_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'cyllo_crm/static/src/js/message.js',
            'cyllo_crm/static/src/js/chatter.js',
            'cyllo_crm/static/src/xml/pinned_messages.xml',
            'cyllo_crm/static/src/xml/crm_lead_compare.xml',
            'cyllo_crm/static/src/js/crm_lead_compare.js',
            'cyllo_crm/static/src/xml/crm_lead_dashboard_templates.xml',
            'cyllo_crm/static/src/js/crm_lead_dashboard.js',
            'cyllo_crm/static/src/xml/crm_lead_list_view_templates.xml',
            'cyllo_crm/static/src/js/crm_lead_list_view.js',
            'cyllo_crm/static/src/css/message.css',

            # Dashboard
            'cyllo_crm/static/src/css/dashboard_style.css',
            'cyllo_crm/static/src/js/dashboard.js',
            'cyllo_crm/static/src/xml/dashboard.xml',
            'https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js',
            'https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js',
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': True,
    'application': False,
}
