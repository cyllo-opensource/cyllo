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
    'name': 'Cyllo Access Management',
    'description' : 'This module is an all in one access manager application'
                    'to simplify access rights management including creating'
                    'user profiles,menu control, button and tab management,'
                    'filters and groups,field rights and domain-based access ',
    'summary' : 'Access Management Module in Cyllo',
    'version': "1.0",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    "depends": ['mail', 'web', 'cyllo_ui_component'],
    'icon': '/cyllo_access_management/static/description/Access-management.svg',
    'data' : [
            'security/cyllo_access_management_security.xml',
            'security/ir.model.access.csv',
            'views/user_profile_views.xml',
            'views/profile_management_views.xml',
            'views/hide_buttons_tabs_views.xml',
            'views/hide_filters_views.xml',
            'views/field_access_views.xml',
            'views/model_access_views.xml',
            'views/domain_access_views.xml',
            'views/res_users_views.xml',
            'views/access_manager_menus.xml',
            'views/login_templates.xml',
        ],
    'assets': {
        'web.assets_backend': [
            'cyllo_access_management/static/src/js/action_list.js',
            'cyllo_access_management/static/src/js/debug_notification.js',
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
