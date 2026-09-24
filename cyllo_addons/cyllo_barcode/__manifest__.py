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
    'name': 'Cyllo Barcode',
    'summary': 'Cyllo Inventory Barcode',
    'description': 'Barcode for the Inventory Adjustments and Transfers',
    'version': "1.0",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'category': 'Warehouse',
    'depends': ['stock_picking_batch', 'mrp_subcontracting'],
    'assets': {
        'web.assets_backend': [
            'cyllo_barcode/static/src/view/**/*',
            'cyllo_barcode/static/src/js/choosePicking.js',
            'cyllo_barcode/static/src/js/choosePicking.xml',
            'cyllo_barcode/static/src/js/cyllo_barcode.js',
            'cyllo_barcode/static/src/js/barcode_adjustment.js',
            'cyllo_barcode/static/src/js/barcode_adjustment_lines.js',
            'cyllo_barcode/static/src/js/barcode_batch.js',
            'cyllo_barcode/static/src/js/barcode_location.js',
            'cyllo_barcode/static/src/js/barcode_location_lines.js',
            'cyllo_barcode/static/src/js/barcode_operation_type.js',
            'cyllo_barcode/static/src/js/barcode_dialog.js',
            'cyllo_barcode/static/src/lib/quagga.js',
            'cyllo_barcode/static/src/xml/barcode_adjustment_templates.xml',
            'cyllo_barcode/static/src/xml/barcode_batch_templates.xml',
            'cyllo_barcode/static/src/xml/barcode_location_templates.xml',
            'cyllo_barcode/static/src/xml/barcode_operation_type_templates.xml',
            'cyllo_barcode/static/src/xml/barcode_templates.xml',
            'cyllo_barcode/static/src/xml/barcode_dialog.xml',
            'cyllo_barcode/static/src/js/barcode_sound_service.js',
            'cyllo_barcode/static/src/scss/style.css',
            'cyllo_barcode/static/src/scss/cyllo_barcode.scss',
        ],
        'web.qunit_suite_tests': [
            'cyllo_barcode/static/src/tests/*'
        ]
    },
    'icon': '/cyllo_barcode/static/description/barcode.svg',
    'data': [
        'reports/cyllo_barcode_report.xml',
        'reports/cyllo_barcode_templates.xml',
        'views/stock_location_views.xml',
        'views/stock_picking_type_views.xml',
        'views/res_config_settings_views.xml',
        'views/ir_actions_client_views.xml',
        'views/stock_picking_views.xml',
        'views/stock_picking_batch_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': True
}