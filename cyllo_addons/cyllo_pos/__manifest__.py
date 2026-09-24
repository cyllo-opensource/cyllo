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
    'name': "Cyllo POS",
    'summary': 'Debranding the default brand from POS',
    'description': 'Install the module to remove all the predefined brands of '
                   'the parent company from POS',
    'version': "1.0",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'category': 'Tools',
    'depends': ['cyllo_base', 'point_of_sale'],
    'data': [
        'views/pos_assets_index.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'cyllo_pos/static/src/**/*',
            'cyllo_pos/static/src/css/style.css',
            'cyllo_pos/static/src/xml/overrides/components/receipt_screen/order_receipt/order_receipt.xml'
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': True,
}
