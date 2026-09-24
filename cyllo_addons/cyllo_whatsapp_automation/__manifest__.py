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
    'name': 'Cyllo Whatsapp Automation',
    'category': 'Marketing',
    'summary': "Build and publish interactive WhatsApp Flows",
    'description': "Design multi-screen WhatsApp Flows, publish them to "
                   "WhatsApp, send them from sales orders and leads, and "
                   "collect customer replies as records with a flow analysis "
                   "report.",
    'version': "1.0",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['cyllo_whatsapp', 'sale_stock', 'sale_management'],
    'data': [
        'security/ir.model.access.csv',
        'security/cyllo_whatsapp_automation_security.xml',
        'data/utm_source.xml',
        'wizards/whatsapp_template_message_views.xml',
        'report/flow_analysis_report_template.xml',
        'views/flow_user_response_views.xml',
        'views/whatsapp_flows_screen_contents_views.xml',
        'views/whatsapp_flows_screens_views.xml',
        'views/whatsapp_flows_views.xml',
        'views/whatsapp_template_views.xml',
        'views/sale_order_template_views.xml',
        'views/sale_order_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'https://www.gstatic.com/charts/loader.js',
            'https://fonts.googleapis.com/css2?family=Inconsolata:wght@200..900&family=Kanit:ital,wght@0,100;0,200;0,300;0,400;0,500;0,600;0,700;0,800;0,900;1,100;1,200;1,300;1,400;1,500;1,600;1,700;1,800;1,900&display=swap',
            '/cyllo_whatsapp_automation/static/src/css/*',
            '/cyllo_whatsapp_automation/static/src/js/*',
            '/cyllo_whatsapp_automation/static/src/xml/*',
        ],
    },
    'images': [],
    'external_dependencies': {'python': ['inflect']},
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
