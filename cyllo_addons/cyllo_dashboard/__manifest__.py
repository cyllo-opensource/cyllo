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
    'name': 'Cyllo User Dashboard',
    "summary": "A dashboard featuring details of the current logged in user",
    "description": """
        A dashboard that displays information about the currently logged-in user. It includes various aspects such as 
        personal details, login history, upcoming activities, system performance insight and also provides access to 
        menus added to shortcuts
    """,
    'version': "1.0",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['cyllo_base'],
    'external_dependencies': {
        'python': ['geocoder']
    },
    'icon': '/cyllo_dashboard/static/description/user-dashboard.svg',
    'data': [
        'security/cyllo_dashboard_security.xml',
        'security/ir.model.access.csv',
        'views/login_user_detail_views.xml',
        'views/change_password_own_views.xml',
        'views/res_users_views.xml',
        'views/shortcut_menu_views.xml',
        'views/cyllo_dashboard_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js',
            'cyllo_dashboard/static/src/js/company_dialog.js',
            'cyllo_dashboard/static/src/js/banner_crop_dialog.js',
            'cyllo_dashboard/static/src/js/cyllo_dashboard.js',
            'cyllo_dashboard/static/src/xml/cyllo_dashboard.xml',
            'cyllo_dashboard/static/src/xml/banner_crop_dialog.xml',
            'cyllo_dashboard/static/src/xml/add_to_shortcuts.xml',
            'cyllo_dashboard/static/src/js/add_to_shortcuts.js',
            'cyllo_dashboard/static/src/js/form_controller.js',
            'cyllo_dashboard/static/src/css/style.css'
        ],
    },
    'uninstall_hook':'uninstall_hook',
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': True,
    'application': False,
}
