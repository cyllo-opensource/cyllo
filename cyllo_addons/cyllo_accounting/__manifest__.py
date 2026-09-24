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
    'name': 'Cyllo Accounting',
    'category': 'Accounting',
    'summary': """Accounting Customizations""",
    'description': "More functionalities on accounting module",
    'version': "1.0",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['web', 'account', 'mail', 'payment'],
    'icon': '/cyllo_base/static/src/icons/invoicing.svg',
    'data': [
        'data/tax_returns_journal.xml',
        'data/ir_actions_server_data.xml',
        'data/account_fiscal_year_data.xml',
        'data/ir_cron_data.xml',
        'data/ir_sequence.xml',
        'security/security.xml',
        'security/ir.model.access.csv',
        'wizards/tax_return_wizard_views.xml',
        'wizards/account_asset_modify_views.xml',
        'wizards/account_bank_transaction_wizard_views.xml',
        'wizards/account_move_lock_views.xml',
        'wizards/import_bank_statement_views.xml',
        'views/account_asset_type_views.xml',
        'views/account_asset_views.xml',
        'views/account_bank_statement_line_views.xml',
        'views/account_fiscal_year_views.xml',
        'views/account_journal_views.xml',
        'views/account_move_line_views.xml',
        'views/account_move_views.xml',
        'views/account_payment_views.xml',
        'views/batch_component_views.xml',
        'views/batch_payment_views.xml',
        'views/online_bank_provider_views.xml',
        'views/res_config_settings_views.xml',
        'views/account_return_views.xml',
        'views/account_return_checks_views.xml',
        'views/cyllo_accounting_menus.xml',

        'reports/ir_actions_report.xml',
        'reports/aged_payable_receivable_templates.xml',
        'reports/bank_book_report_templates.xml',
        'reports/report_aged_payable.xml',
        'reports/report_aged_receivable.xml',
        'reports/report_profit_n_loss.xml',
        'reports/report_balance_sheet.xml',
        'reports/tax_report_template.xml',
        'reports/report_trial_balance.xml',
        'reports/report_partner_ledger.xml',
        'reports/report_bank_book.xml',
        'reports/report_cash_book.xml',
        'reports/report_general_ledger.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'https://cdnjs.cloudflare.com/ajax/libs/moment.js/2.30.1/moment.min.js',
            '/cyllo_accounting/static/src/js/*.js',
            '/cyllo_accounting/static/src/js/accounting_report_base/*',
            '/cyllo_accounting/static/src/js/pnl_report/*',
            '/cyllo_accounting/static/src/js/generalLedgerReport/*',
            '/cyllo_accounting/static/src/views/list/*',
            '/cyllo_accounting/static/src/views/reconcile/*',
            '/cyllo_accounting/static/src/views/reconcile/components/**/*',
            '/cyllo_accounting/static/src/**/*',
        ],
    },
    'external_dependencies': {'python': ['pandas', 'PyQifParser', 'openpyxl', 'xlrd']},
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': True,
    'application': True,
    'post_init_hook': '_post_init_hook',
    'uninstall_hook': 'uninstall_hook',
}
