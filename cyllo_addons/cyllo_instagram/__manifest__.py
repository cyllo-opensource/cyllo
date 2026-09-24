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
    'name': 'Cyllo Instagram',
    'category': 'Marketing',
    'summary': """This module is used to manage instagram account""",
    'description': """This module is used to manage instagram account and also
     create post in the configured account""",
    'version': "1.0",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['mail', 'crm', 'cyllo_social_media_marketing'],
    'icon': '/cyllo_instagram/static/description/instagram.svg',
    'data': [
        'security/ir.model.access.csv',
        'security/social_insta_account_security.xml',
        'data/mail_message_subtype.xml',
        'views/ir_attachment_views.xml',
        'views/social_media_post_views.xml',
        'views/res_partner_views.xml',
        'views/social_insta_account_views.xml',
        'views/social_media_feed_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'cyllo_instagram/static/src/js/instagram_comments.js',
            'cyllo_instagram/static/src/xml/instagram_comment_template.xml',
            'cyllo_instagram/static/src/xml/chat_window_template.xml',
            'cyllo_instagram/static/src/systray/ig_systray.xml',
            'cyllo_instagram/static/src/systray/ig_systray.js',
            'cyllo_instagram/static/src/xml/chatter.xml',
            'cyllo_instagram/static/src/js/chatter.js',
            'cyllo_instagram/static/src/xml/suggestedReciepient.xml',
            'cyllo_instagram/static/src/js/streams/stream_item_insta.js',
            'cyllo_instagram/static/src/js/post_platform_account_ig.js',
        ],
    },
    'images': [],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
