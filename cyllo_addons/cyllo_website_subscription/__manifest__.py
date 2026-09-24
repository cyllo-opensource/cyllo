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
    'name': "Cyllo Ecommerce Subscription",
    'summary': "This module extends the Website Sale functionality to support complex, time-based subscription pricing rules",
    'description': """Extends the e-commerce product page to allow for dynamic subscription plan selection and includes custom pricing logic.""",
    'version': "1.0",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'data': [
             'views/website_sale_templates.xml',
             ],
    'assets': {
        'web.assets_frontend': [
            'cyllo_website_subscription/static/src/js/website_sale.js',
            'cyllo_website_subscription/static/src/js/add_to_cart_notification.js',
        ],
    },
    'depends': ['cyllo_base','cyllo_subscription','cyllo_website_sale'],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': True,
}
