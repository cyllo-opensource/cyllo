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
    'name': 'Cyllo Purchase Digitization',
    'category': 'Purchases',
    'summary': """
     Digitize Purchase Quotation Automatically or Manually.""",
    'description': """This module helps to retrieve data from pdf files and
     generate the field values of purchase module automatically or manually.""",
    'version': "1.0",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['purchase', 'cyllo_ocr_digitization', 'cyllo_purchase'],
    'data': [
        'security/ir.model.access.csv',
        'views/purchase_digitization_views.xml',
        'views/purchase_order_views.xml',
        'views/res_config_settings_views.xml',
        'wizard/digitization_ai_wizard.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'cyllo_purchase_digitization/static/src/js/cyllo_purchase_digitization.js',
            'cyllo_purchase_digitization/static/src/xml/cyllo_purchase_digitization.xml',
        ]
    },
    'external_dependencies': {
        'python': ['pandas', 'camelot-py',
                   'opencv-python', 'PyMuPDF']
    },
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
