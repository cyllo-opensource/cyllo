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
    'name': 'Cyllo Grid view',
    'category': 'Others',
    'summary': 'Cyllo Grid View',
    'description': """This module helps to add new grid view in the timesheet module""",
    'version': "1.0",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['hr_timesheet', 'sale_management'],
    'icon':'/cyllo_timesheet_grid/static/description/grid.svg',
    'data': [
        'views/cyllo_timesheet_grid_views.xml',
        'views/res_config_settings_views.xml',
             ],
    'assets': {
        'web.assets_backend': [
            'cyllo_timesheet_grid/static/src/views/GridViews/*.js',
            'cyllo_timesheet_grid/static/src/views/GridViews/*.xml',
            'cyllo_timesheet_grid/static/src/views/GridViews/grid_view.scss'
        ],
    },
    'pre_init_hook': '_pre_init_cyllo_timesheet_grid',
    'uninstall_hook': '_uninstall_hook_cyllo_timesheet_grid',
    'license': 'LGPL-3',
    'installable': True,
    'application': True,
    'auto_install': True,
}
