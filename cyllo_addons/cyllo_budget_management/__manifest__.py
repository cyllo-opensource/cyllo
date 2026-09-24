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
    'name': 'Cyllo Budget Management',
    'category': 'Accounting',
    'summary': """Configure Budget and Debt Management Easily """,
    'description': "We can create Budget , Track the expense and cost according to the given criteria."
                   "Also easily manages the Debt Management System",
    'version': "1.0",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['cyllo_base', 'cyllo_accounting'],
    'icon': '/cyllo_budget_management/static/description/budget-management.svg',
    'data': [
        'security/ir_rule.xml',
        'security/ir.model.access.csv',
        'security/security.xml',
        'data/ir_sequence_data.xml',
        'data/ir_cron_data.xml',
        'data/mail_template_data.xml',
        'data/ir_actions_server_data.xml',
        'reports/budget_report_template.xml',
        'reports/debt_report_template.xml',
        'reports/ir_action_report.xml',
        'wizards/debt_payback_wizard.xml',
        'views/analytic_account_views.xml',
        'views/budget_lines_configurator_view.xml',
        'views/budget_budget_view.xml',
        'views/budget_lines_view.xml',
        'views/debt_management.xml',
        'views/budget_management_menu.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
    'post_init_hook': '_post_init_hook',
}
