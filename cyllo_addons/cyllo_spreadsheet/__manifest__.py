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
    'name': 'Cyllo Spreadsheet',
    'description': 'This module is used to add features in spreadsheet module',
    'summary': 'Cyllo Spreadsheet',
    'version': "1.0",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'category': 'Others',
    'depends': ["spreadsheet"],
    'data': [
        'security/spreadsheet_security.xml',
        'security/ir.model.access.csv',
        'views/spreadsheet_views.xml',
    ],
    'icon': '/cyllo_spreadsheet/static/description/spreadsheet.svg',
    'assets': {
        'web.assets_backend': [
            'cyllo_spreadsheet/static/src/style.css',
            'cyllo_spreadsheet/static/src/actions/*',
            'cyllo_spreadsheet/static/src/hooks/*',
            'cyllo_spreadsheet/static/src/lib/*',  # version compatabile with cyllo_analytics
            'cyllo_spreadsheet/static/src/views/**/*',
            "cyllo_spreadsheet/static/src/main/spreadsheetLoader.js",
        ],
        "spreadsheet.o_spreadsheet": [
            "cyllo_spreadsheet/static/src/main/main.js",
            "cyllo_spreadsheet/static/src/spreadsheet/*",
            "cyllo_spreadsheet/static/src/topMenuRegistry/**/*",
        ],

    },
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': True,
}
