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
    'name': 'Cyllo Accounting Follow-ups',
    'category': 'Accounting',
    'summary': """Accounting Follow-ups""",
    'description': "Follow-up features on accounting module",
    'version': "1.0",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['sale_management', 'cyllo_accounting'],
    'data': [
        'data/mail_template_data.xml',
        'data/ir_cron_data.xml',
        'security/cyllo_accounting_follow_up_security.xml',
        'security/ir.model.access.csv',
        'views/accounting_follow_up_line_views.xml',
        'views/account_move_views.xml',
        'views/res_partner_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'cyllo_accounting_follow_up/static/src/css/*',
            '/cyllo_accounting_follow_up/static/src/Many2OneWidget/many2oneWidget.xml',
            '/cyllo_accounting_follow_up/static/src/Many2OneWidget/many2oneWidget.js'
        ]
    },
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
