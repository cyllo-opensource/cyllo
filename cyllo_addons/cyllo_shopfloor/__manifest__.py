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
    'name': 'Cyllo Shop Floor',
    'summary': 'Shopfloor Interface',
    'description': 'Provides a tablet-friendly shop floor screen where '
                   'operators pick a work center and start, pause, block or '
                   'finish work orders, add or scrap components and reroute '
                   'operations.',
    'version': "1.0",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['mrp', 'bus', 'web', 'hr'],
    'icon': '/cyllo_shopfloor/static/description/shop-floor.svg',
    'data': [
        'security/cyllo_shopfloor_security.xml',
        'security/ir.model.access.csv',
        'data/automated_mo_crone.xml',

        'views/cyllo_shopfloor_views.xml',
        'views/mrp_production_views.xml',
        'views/mrp_bom_views.xml',

        'wizards/mrp_add_component_wizard_views.xml',
        'wizards/mrp_scrap_component_wizard_views.xml',
        'wizards/mrp_reroute_wizard_views.xml',
        'wizards/mrp_add_workorder_wizard_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'cyllo_shopfloor/static/src/css/style.css',
            'cyllo_shopfloor/static/src/js/cyllo_shopfloor.js',
            'cyllo_shopfloor/static/src/xml/cyllo_shopfloor_template.xml',
            'cyllo_shopfloor/static/src/js/backend_listener.js',
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
    'application': True,
}
