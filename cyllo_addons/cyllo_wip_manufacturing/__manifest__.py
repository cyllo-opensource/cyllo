# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cyllo(<https://www.cyllo.com>)
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
    'name': 'Cyllo Manufacturing WIP Accounting',
    'summary': 'Manufacturing Work-In-Progress (WIP) Accounting',
    'description': 'Post balanced work-in-progress journal entries for '
                   'manufacturing orders with a draft reversal entry, using '
                   'the WIP journal and accounts configured per company.',
    'version': "1.0",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'category': 'Manufacturing/Manufacturing',
    'depends': [
        'mrp',
        'cyllo_accounting',
        'stock_account',
        'cyllo_anglo_saxon',
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizard/mrp_wip_accounting_wizard_views.xml',
        'views/res_config_settings_views.xml',
        'views/mrp_production_views.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': True,
    'application': False,
}
