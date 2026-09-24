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
    'name': 'Cyllo POS Kitchen Screen',
    'category': 'Point Of Sale',
    'summary': 'POS Kitchen Screen facilitates sending certain orders '
               'automatically to the kitchen.The POS Kitchen Screen allows for'
               'the customization of order views, so that staff can see the '
               'information that is most important to them.',
    'description': 'The POS Kitchen Screen in Cyllo is a feature that '
                   'allows restaurant staff to view and manage orders in '
                   'real-time from the kitchen. This screen provides a clear '
                   'and organized display of all active orders, enabling '
                   'kitchen staff to prioritize and manage their tasks '
                   'efficiently.',
    'version': "1.0",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'icon':'/cyllo_pos_kitchen_screen/static/description/pos-kitchen-screen.svg',
    'depends': ['pos_restaurant'],
    'data': [
        'security/pos_kitchen_screen_groups.xml',
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/kitchen_screen_sequence_data.xml',
        'views/kitchen_screen_views.xml',
        'views/cyllo_pos_kitchen_screen_menu_views.xml',
        'views/pos_order_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'cyllo_pos_kitchen_screen/static/src/js/fields_load.js',
            'cyllo_pos_kitchen_screen/static/src/js/order_payment.js',
            'cyllo_pos_kitchen_screen/static/src/js/order_button.js',
        ],
        'web.assets_backend': [
            'cyllo_pos_kitchen_screen/static/src/css/kitchen_screen.css',
            'cyllo_pos_kitchen_screen/static/src/js/kitchen_screen.js',
            'cyllo_pos_kitchen_screen/static/src/xml/kitchen_screen_templates.xml',
            'https://code.jquery.com/jquery-1.10.2.min.js',
            'https://unpkg.com/scrollreveal@4.0.0/dist/scrollreveal.min.js',
            'https://fonts.googleapis.com',
            'https://cdn.jsdelivr.net/npm/popper.js@1.16.1/dist/umd/popper.min.js',
            'https://cdn.jsdelivr.net/npm/bootstrap@4.6.2/dist/js/bootstrap.bundle.min.js',
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
