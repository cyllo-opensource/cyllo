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
    'name': 'Cyllo LinkedIn',
    'category': 'Marketing',
    'summary': 'LinkedIn Integration for Cyllo',
    'description': 'LinkedIn Integration for Cyllo',
    'version': "1.0",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'icon': '/cyllo_linkedin/static/description/linkedin.svg',
    'depends': ['mail', 'auth_oauth', 'cyllo_social_media_marketing'],
    'data': [
        'security/ir.model.access.csv',
        'security/linkedin_security.xml',
        'data/auth_linkedin_data.xml',
        'views/linkedin_account_views.xml',
        'views/social_media_post_views.xml',
        'views/oauth_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'cyllo_linkedin/static/src/js/connect_platform_linkedin.js',
            'cyllo_linkedin/static/src/js/streams/stream_item_li.js',
            'cyllo_linkedin/static/src/js/post_platform_account_li.js',
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
