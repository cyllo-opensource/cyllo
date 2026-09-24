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
    'name': 'Cyllo Manufacturing MPS',
    'summary': 'Master production scheduling with automated replenishment and order creation',
    'description': """
        Adds an MPS dashboard for planning product demand, replenishment, and stock coverage.
        Supports manual or automated replenishment, purchase order creation, manufacturing order creation,
        and period-based planning for buy or manufacture routes.
    """,
    'version': "1.0",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['mrp'],

    'data': [
        'security/ir.model.access.csv',
        'security/mps_group.xml',
        'security/mps_company_rule.xml',
        'views/mrp_mps_schedule_client_action.xml',
        'views/mrp_mps_schedule_views.xml',
        'views/res_config_settings_views.xml',
        'data/mps_cron.xml',

    ],
    'assets': {
        'web.assets_backend': [
            'cyllo_manufacturing_mps/static/src/xml/mrp_mps_schedule.xml',
            'cyllo_manufacturing_mps/static/src/js/mrp_mps_schedule.js',

        ],
    },

    'license': 'LGPL-3',
    'installable': True,
    'auto_install': True,
    'application': False,
}
