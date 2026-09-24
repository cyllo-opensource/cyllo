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
    'name': 'Cyllo Accounting PDC',
    'category': 'Accounting',
    'summary': """Accounting Post Dated Cheque""",
    'description': "Post Dated Cheque management on accounting module",
    'version': "1.0",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['account_check_printing', 'cyllo_accounting'],
    'data': [
        'data/check_layout.xml',
        'data/account_payment_method_data.xml',
        'security/ir.model.access.csv',
        'wizards/account_pdc_payment_register.xml',
        'wizards/account_pdc_bounce_reason.xml',
        'reports/report_pdc_payment_templates.xml',
        'reports/reports.xml',
        'views/account_pdc_payment_views.xml',
        'views/account_move_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': True,
    'application': False,
    'post_init_hook': '_post_init_account',
}
