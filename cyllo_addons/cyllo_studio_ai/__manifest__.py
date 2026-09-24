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
    'name': 'Cyllo Studio AI',
    'category': 'Productivity',
    'summary': """Creating new modules""",
    'description': """The module helps you to create new module using AI""",
    'version': "1.0",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['web', 'cyllo_web', 'cyllo_studio', 'mail'],
    'data': [
        'security/ir.model.access.csv',
    ],
    'assets': {
        'cyllo_studio.assets_backend': [
            'cyllo_studio_ai/static/src/js/root/studio_wrapper_main.js',
            'cyllo_studio_ai/static/src/js/root/studio_wrapper_main.xml',
            'cyllo_studio_ai/static/src/js/web_client/action_container.js',
            'cyllo_studio_ai/static/src/js/web_client/action_container.xml',
            'cyllo_studio_ai/static/src/js/web_client/navbar.js',
            'cyllo_studio_ai/static/src/js/new_app_options/new_app_options_templates.xml',
            'cyllo_studio_ai/static/src/js/new_app_options/new_app_options.js',
            'cyllo_studio_ai/static/src/js/dialog/PromptDialog.js',
            'cyllo_studio_ai/static/src/js/dialog/PromptDialog.xml',
            'cyllo_studio_ai/static/src/css/ai_app_style.css',

        ],
    },
    'license': 'LGPL-3',
    'installable': True,
    'application': True,
    'auto_install': False,
}
