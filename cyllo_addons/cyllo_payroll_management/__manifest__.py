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
    'name': 'Cyllo Payroll Management',
    'category': 'Human Resources',
    'summary': """Used to manage the payroll module""",
    'description': """The module helps you to manage the employee contract, and payroll management in cyllo.""",
    'version': "1.0",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': [
        'hr_contract',
        'mail',
        'hr_work_entry',
        'hr_attendance',
        'hr_work_entry_contract',
        'hr_work_entry_holidays',
        'contacts',
        'hr_holidays',
        'hr_expense',
        'portal',
        'website',
        'cyllo_commission',
        'cyllo_accounting',
    ],
    'icon': '/cyllo_payroll_management/static/description/payroll.svg',
    'data': [
        'security/cyllo_payroll_management_groups.xml',
        'security/cyllo_payroll_management_rules.xml',
        'security/ir.model.access.csv',
        'reports/report_resignation_request.xml',
        'data/employee_salary_rule_category_data.xml',
        'data/account_journal_data.xml',
        'data/employee_payslip_other_input_data.xml',
        'data/employee_salary_rule_data.xml',
        'data/employee_salary_structure_data.xml',
        'data/ir_sequence_data.xml',
        'data/ir_cron_data.xml',
        'data/decimal_precision_data.xml',
        'data/mail_template_data.xml',
        'views/hr_contract_views.xml',
        'views/employee_salary_structure_views.xml',
        'views/hr_payroll_structure_type_views.xml',
        'views/employee_salary_rule_category_views.xml',
        'views/employee_salary_rule_views.xml',
        'views/employee_payslip_views.xml',
        'views/employee_payslip_batch_views.xml',
        'views/hr_employee_views.xml',
        'views/hr_work_entry_type_views.xml',
        'views/employee_resignation_views.xml',
        'views/resigned_reasons_views.xml',
        'views/gratuity_configuration_views.xml',
        'views/gratuity_settlement_views.xml',
        'views/employee_training_period_views.xml',
        'views/employee_payslip_other_input_views.xml',
        'views/employee_salary_attachment_views.xml',
        'views/hr_expense_sheet_views.xml',
        'views/hr_leave_type_views.xml',
        'views/account_move_views.xml',
        'wizards/batch_payslip_mark_paid.xml',
        'wizards/resignation_request_confirm.xml',
        'wizards/employee_payslip_batch_list.xml',
        'wizards/hr_advance_salary_close.xml',
        'reports/report_employee_payslip.xml',
        'views/hr_payroll_dashboard_views.xml',
        'views/hr_advance_salary_views.xml',
        'views/salary_calculator_views.xml',
        'views/hr_employee_payroll_view.xml',
        'views/cyllo_payroll_management_menu_views.xml',
        'views/res_config_settings_views.xml',
        'views/res_company_views.xml',
        'views/commission_report_views.xml',

    ],
    'assets': {
        'web.assets_backend': [
            'cyllo_payroll_management/static/src/css/payroll_dashboard.css',
            'cyllo_payroll_management/static/src/js/payroll_dashboard.js',
            'cyllo_payroll_management/static/src/xml/payroll_dashboard.xml',
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
    'application': True,
    'auto_install': False,
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
}
