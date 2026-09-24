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
    'name': "Cyllo Website Branding",
    'summary': "Debranding default brand and replaces with Cyllo",
    'description': """
        This module helps to removes any pre-existing branding and replaces it with "Cyllo" as the new brand.
    """,
    'version': "1.0",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['cyllo_base', 'website'],
    'data': [
        'templates/website_templates.xml',
        'templates/portal_templates.xml'
    ],
    'assets': {
        'web.assets_backend': [
            '/cyllo_website/static/src/css/style.css',
            '/cyllo_website/static/src/js/new_content_form_controller.js',
            # '/cyllo_website/static/src/js/menu_sidebar.js',
            '/cyllo_website/static/src/js/navbar.js',
        ],

        'web.assets_frontend': [
            '/cyllo_website/static/src/css/website_template.css',
            '/cyllo_website/static/src/js/portal_template.js',
        ],

        'web._assets_primary_variables': [
            '/cyllo_website/static/src/scss/cyllo_palette.scss',
        ],
    },
    'pre_init_hook': '_pre_init_favicon',
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': True
}
