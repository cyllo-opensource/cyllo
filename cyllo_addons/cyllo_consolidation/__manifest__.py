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
    'name': 'Cyllo Consolidation',
    'category': 'Accounting/Accounting',
    'summary': """The "cyllo_consolidation" Cyllo app streamlines data management by consolidating related records or 
    information within the Cyllo environment.""",
    'description': """The app merges, aggregates, or organizes data from different sources or modules, providing users 
    with a comprehensive view and enhancing decision-making and data handling efficiency.""",
    'version': "1.0",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['mail', 'cyllo_base', 'cyllo_accounting'],
    'icon':'/cyllo_consolidation/static/description/consolidaton.svg',
    'data': [
        'data/ir_actions_client_data.xml',
        'security/ir.model.access.csv',
        'security/consolidation_security.xml',
        'reports/consolidated_balance_templates.xml',
        'reports/reports.xml',
        'views/consolidation_chart_views.xml',
        'views/consolidation_account_views.xml',
        'views/consolidation_group_views.xml',
        'views/consolidation_journal_views.xml',
        'views/consolidation_period_views.xml',
        'views/cyllo_consolidation_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'cyllo_consolidation/static/src/js/consolidated_balance.js',
            'cyllo_consolidation/static/src/xml/consolidated_balance_templates.xml',
            'cyllo_consolidation/static/src/scss/consolidated_balance.scss'
        ]
    },
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
