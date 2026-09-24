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
    'name': 'Cyllo Repair Floor',
    'summary': 'Tablet-friendly interface for Repair Technicians',
    'description': 'Provides a Repair Floor screen where technicians follow '
                   'open repair orders on cards, edit repair lines and record '
                   'repair notes from a touch-friendly interface.',
    'version': "1.0",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['cyllo_repair', 'repair'],
    'icon': '/cyllo_shopfloor_repair/static/description/repair-floor.svg',
    'data': [
        'security/shopfloor_repair_security.xml',
        'security/ir.model.access.csv',
        'views/repair_floor_action.xml',
        'views/repair_order_views.xml',
        'views/repair_notes_views.xml',

        'wizard/edit_repair_line_views_wizard.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'cyllo_shopfloor_repair/static/src/components/**/*.js',
            'cyllo_shopfloor_repair/static/src/components/**/*.xml',
            'cyllo_shopfloor_repair/static/src/components/**/*.scss',
            'cyllo_shopfloor_repair/static/src/repair_card/**/*.js',
            'cyllo_shopfloor_repair/static/src/repair_card/**/*.xml',
            'cyllo_shopfloor_repair/static/src/repair_card/**/*.scss',
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
    'application': True,
}
