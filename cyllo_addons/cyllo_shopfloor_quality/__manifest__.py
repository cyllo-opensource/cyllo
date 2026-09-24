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
    'name': 'Cyllo Shopfloor Quality',
    'category': 'Manufacturing',
    'summary': 'Quality Check button integration for the Shopfloor view',
    'description': 'Bridge module that adds a Quality Check button and Quality '
                   'Alert option to manufacturing order cards in the Shop '
                   'Floor screen when quality checks are configured.',
    'version': "1.0",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['cyllo_shopfloor', 'cyllo_quality_mrp'],
    'assets': {
        'web.assets_backend': [
            'cyllo_shopfloor_quality/static/src/js/shopfloor_quality.js',
            'cyllo_shopfloor_quality/static/src/xml/shopfloor_quality_template.xml',
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': True,
}
