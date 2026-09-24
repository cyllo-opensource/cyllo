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
    'name': 'Cyllo Youtube',
    'category': 'Extra tool',
    'summary': "Integrate YouTube functionality into the Cyllo Social Media Marketing module.",
    'description': """This module extends the functionality of the Cyllo Social Media Marketing module by integrating YouTube features. It allows users to manage YouTube accounts, channels, and posts """,
    'version': "1.0",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['mail', 'crm', 'cyllo_social_media_marketing'],
    'icon': '/cyllo_youtube/static/description/youtube.svg',
    'data': [
        'security/youtube_account_security.xml',
        'security/ir.model.access.csv',
        'views/youtube_account_views.xml',
        'views/youtube_channel_views.xml',
        'views/social_media_feed_views.xml',
        'views/social_media_post_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'cyllo_youtube/static/src/xml/youtube_comment_template.xml',
            'cyllo_youtube/static/src/js/youtube_comments.js',
            'cyllo_youtube/static/src/js/streams/stream_item_youtube.js',
            'cyllo_youtube/static/src/js/connect_platform_youtube.js',
            'cyllo_youtube/static/src/js/post_platform_account_yt.js',
            'cyllo_youtube/static/src/js/youtube_media_upload_field.js',
        ],
    },
    'images': [
        'static/src/img/youtube.png',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
