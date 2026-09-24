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
    'name': 'Cyllo App Mass Install',
    'summary': """Onboarding view after login for the first time""",
    'description': "This module gives Onboarding view after login for the first time",
    'version': "1.0",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['web', 'base'],
    'data': [
        'views/massive_app_install_templates.xml',
        'views/res_users_views.xml'
    ],
    'assets': {
        'web.assets_backend': [
            'cyllo_app_mass_install/static/src/js/app.js',
            'cyllo_app_mass_install/static/src/js/selected_app_details.js',
            'cyllo_app_mass_install/static/src/js/app_drawer.js',
            'cyllo_app_mass_install/static/src/xml/app_templates.xml',
            'cyllo_app_mass_install/static/src/xml/selected_app_details_templates.xml',
            'cyllo_app_mass_install/static/src/xml/app_drawer_templates.xml',
            'cyllo_app_mass_install/static/src/css/massive_app_style.css',
            'cyllo_app_mass_install/static/src/js/error_dialog.js',
        ],
    },
    'uninstall_hook': 'uninstall_hook',
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': True,
    'sequence': 10000,
}
