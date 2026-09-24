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
    'name': 'Cyllo Quality Management',
    'category': 'Productivity',
    'summary': """Quality Management""",
    'description': "Module for ensuring quality checks",
    'version': "1.0",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['hr', 'stock', 'cyllo_web', 'sales_team'],
    'icon': '/cyllo_quality/static/description/quality-control-white.svg',
    'data': [
        'data/ir_sequenece_data.xml',
        'data/email_template_quality_control_point.xml',
        'data/quality_alert_stage_data.xml',
        'data/inspection_type_data.xml',
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/inspection_action_views.xml',
        'views/quality_alert_views.xml',
        'views/quality_alert_stage_views.xml',
        'views/quality_control_point_views.xml',
        'views/quality_check_views.xml',
        'views/quality_team_views.xml',
        'views/product_product.xml',
        'views/product_template_views.xml',
        'views/stock_lot_views.xml',
        'views/stock_picking_views.xml',
        'views/menu_item_views.xml',
        'wizards/alert_warning_views.xml',
        'wizards/quality_check_instruction_views.xml',

    ],
    'assets': {
        'web.assets_backend': [
            'cyllo_quality/static/src/js/views/**/*',
            'cyllo_quality/static/src/js/components/**/*',
        ],
    },
    'demo': [
        'demo/cyllo_quality_demo.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': True,
}
