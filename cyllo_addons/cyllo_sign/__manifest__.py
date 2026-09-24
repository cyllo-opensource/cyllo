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
    "name": "Cyllo Sign",
    "summary": """Allow to sign documents inside Cyllo""",
    "description": """This module help users to sign pdf documents inside Cyllo""",
    'version': "1.0",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    "depends": ["cyllo_base", "mail", "portal", "website", "cyllo_portal", 'payment'],
    'icon': '/cyllo_sign/static/description/sign.svg',
    "data": [
        'data/sign_data.xml',
        'data/email_template_data.xml',
        'data/ir_cron_data.xml',
        'security/sign_security.xml',
        'security/ir.model.access.csv',
        'wizards/sign_generate_views.xml',
        'views/sign_template_views.xml',
        'views/sign_field_views.xml',
        'views/sign_role_views.xml',
        'views/sign_request_views.xml',
        'views/sign_tag_views.xml',
        'templates/sign_request_templates.xml',
        'templates/templates.xml',

    ],
    "assets": {
        'cyllo_sign.assets_sign_main': [
            'cyllo_sign/static/src/js/sign_wrapper.js',
            'cyllo_sign/static/src/js/main.js',
        ],
        "web.assets_backend": [
            'https://cdn.jsdelivr.net/npm/pdfjs-dist/build/pdf.min.js',
            'cyllo_sign/static/src/css/cyllo_sign.css',
            'cyllo_sign/static/src/components/kanban_controller/kanban_renderer.js',
            'cyllo_sign/static/src/components/kanban_controller/kanban_controller.js',
            'cyllo_sign/static/src/components/kanban_controller/kanban_controller.xml',
            'cyllo_sign/static/src/components/kanban_controller/kanban_record.js',
            'cyllo_sign/static/src/js/dialog/dialogService.js',
            'cyllo_sign/static/src/utils/**/*',
            'cyllo_sign/static/src/js/sign_configure/**/*',
            'cyllo_sign/static/src/lib/dragula/**/*',
        ],
        'cyllo_sign.assets_sign': [
            ('include', 'web.assets_backend'),
            ('include', 'cyllo_sign.assets_sign_main'),
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': True,
}
