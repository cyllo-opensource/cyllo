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
    'name': 'Cyllo Portal',
    'summary': 'This module contains the base code for cyllo customer portal',
    'description': 'This module contains the base code for cyllo customer '
                   'portal.The controllers, templates, and JavaScript files '
                   'help update the styles and functionality for the customer '
                   'portal of the Cyllo modules.',
    'version': "1.0",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['payment','portal'],
    'data': [
        'views/portal_templates.xml',
        'views/portal_views.xml',
        'views/portal_add_address_templates.xml',
        'views/portal_address_edit_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'cyllo_portal/static/src/css/cyllo_portal.css',
            'cyllo_portal/static/src/js/cyllo_portal.js',
            'cyllo_portal/static/src/js/cyllo_portal_sidebar.js',
        ],
        'web._assets_primary_variables': [
            'cyllo_portal/static/src/scss/cyllo_palette.scss',
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': True,
    'application': False,
}
