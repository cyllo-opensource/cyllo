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
    'name': "Cyllo Commission",
    'description': 'Commission module helps to create and set commission plans for Salesteam and Salesperson to increase their Productivity',
    'summary': 'Cyllo Commission',
    'version': "1.0",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['cyllo_base', 'cyllo_crm', 'mail', 'sale_margin', 'website'],
    'data': [
        # Security
        'security/ir.model.access.csv',
        'security/commission_report_rule.xml',

        # Data
        'data/ir_cron_data.xml',
        'data/mail_template_data.xml',
        'data/commission_type_data.xml',


        # Views
        'views/commission_templates.xml',
        'views/commission_thank_you_template.xml',
        'views/commission_plan_views.xml',
        'views/commission_plan_target_commission_views.xml',
        'views/commission_report_views.xml',
        'views/commission_type_views.xml',
        'views/commission_menu_views.xml',
        'views/sale_order_views.xml',

        #Reports
        'reports/commission_templates.xml'
    ],
    'assets': {
        'web.assets_backend': [
            'cyllo_commission/static/src/js/dashboard.js',
            'cyllo_commission/static/src/xml/dashboard.xml',
            'cyllo_commission/static/src/js/filters.js',
            'cyllo_commission/static/src/js/graphs.js',
            'cyllo_commission/static/src/js/summary_cards.js',
            'cyllo_commission/static/src/js/sales_performance.js',
            'cyllo_commission/static/src/js/commission_distribution.js',
            'cyllo_commission/static/src/js/plan_cards.js',
            'cyllo_commission/static/src/js/leaderboard.js',
            'cyllo_commission/static/src/js/performance_analysis.js',
            'cyllo_commission/static/src/css/dashboard.css',
            'https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js',
            'https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js'
        ],
        'web.assets_frontend': [
            'cyllo_commission/static/src/js/commission_template.js',
            'cyllo_commission/static/src/css/commission_templates.css',
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
