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
    'name': 'Cyllo Base',
    'description': 'This is the base module for Cyllo',
    'summary': 'Base module for Cyllo',
    'version': "1.0",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'category': 'Hidden',
    'depends': ['base', 'base_setup', 'base_import', 'web', 'mail', 'mail_bot', 'web_hierarchy'],
    'data': [
        'security/ir.model.access.csv',
        'security/sticky_note_security.xml',
        'data/field_widget_data.xml',
        'data/mail_templates_email_layout.xml',
        'data/auth_signup_mail_templates.xml',
        'views/res_users_views.xml',
        'views/ir_model_fields_views.xml',
        'views/ir_module_views.xml',
        'views/ir_model_views.xml',
        'views/res_partner_views.xml',
        'views/res_config_settings_views.xml',
        'views/webclient_templates.xml',
        'wizards/field_create_views.xml',
    ],
    'external_dependencies': {"python": ["python-docx"]},
    'assets': {
        'web.assets_backend': [
            'https://fonts.googleapis.com/css2?family=Inter:wght@100..900&family=Plus+Jakarta+Sans:ital,wght@0,200..800;1,200..800&display=swap',
            '/cyllo_base/static/src/font/remixicon.eot',
            '/cyllo_base/static/src/font/remixicon.ttf',
            '/cyllo_base/static/src/font/remixicon.woff',
            '/cyllo_base/static/src/font/remixicon.woff2',
            '/cyllo_base/static/src/xml/*.xml',
            '/cyllo_base/static/src/js/*.js',
            '/cyllo_base/static/src/webclient/*.js',
            '/cyllo_base/static/src/webclient/*.xml',
            '/cyllo_base/static/src/js/sticky_notes/*.js',
            '/cyllo_base/static/src/xml/sticky_notes/*.xml',
            '/cyllo_base/static/src/js/base_docx/cyllo_base_docx.js',
            '/cyllo_base/static/src/js/base_xlsx/cyllo_base_xlsx.js',
            '/cyllo_base/static/src/js/journal_dashboard_graph/*.js',
            '/cyllo_base/static/description/icon.svg',
            'https://cdn.jsdelivr.net/npm/@johanaarstein/dotlottie-player@1.5.23/dist/index.min.js'
        ],

        'web.assets_frontend': [
            '/cyllo_base/static/src/font/remixicon.eot',
            '/cyllo_base/static/src/font/remixicon.ttf',
            '/cyllo_base/static/src/font/remixicon.woff',
            '/cyllo_base/static/src/font/remixicon.woff2',
            '/cyllo_base/static/src/font/cyllofont-Bold.woff2',
            '/cyllo_base/static/src/font/Cyllo-Font-Medium.woff2',
            '/cyllo_base/static/src/font/cyllofont-Regular.woff2',
            '/cyllo_base/static/src/font/cyllofont-Semibold.woff2',
            '/cyllo_base/static/src/font/cyllofont-Extrabold.woff2',
            '/cyllo_base/static/src/font/Cyllo-Font-Bold.woff2',
            '/cyllo_base/static/src/font/Baloo2-VariableFont.ttf',
        ],

        'web.qunit_suite_tests': [
            'cyllo_dynamic_field/static/src/tests/form_controller_patch_tests.js',
        ],

        'web.assets_clickbot': [
            ('replace', 'web/static/src/webclient/clickbot/clickbot.js', '/cyllo_base/static/src/webclient/clickbot/clickbot.js'),
        ],
    },
    'uninstall_hook': 'uninstall_hook',
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
    'post_init_hook': 'post_init_hook'
}
