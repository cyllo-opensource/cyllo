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
    'name': 'Cyllo Social Media Marketing',
    'category': 'Marketing/Social Media Marketing',
    'summary': "Base module for Social Media Marketing",
    'description': "Base module for Social Media Marketing and for all"
                   " depending module",
    'version': "1.0",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['mail', 'crm', 'utm','mass_mailing'],
    'icon': '/cyllo_social_media_marketing/static/description/social-marketing.svg',
    'data': [
        'security/social_media_marketing_security.xml',
        'security/ir.model.access.csv',
        'data/ir_cron.xml',
        'views/social_media_post_views.xml',
        'views/utm_campaign_views.xml',
        'wizard/social_media_post_schedule_wizard_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'cyllo_social_media_marketing/static/src/js/channel_selector.js',
            'cyllo_social_media_marketing/static/src/js/messaging_menu.js',
            'cyllo_social_media_marketing/static/src/js/chat_window_service.js',
            'cyllo_social_media_marketing/static/src/js/social_post_preview.js',
            'cyllo_social_media_marketing/static/src/xml/social_post_preview.xml',
            'cyllo_social_media_marketing/static/src/scss/social_post_preview.scss',
            'cyllo_social_media_marketing/static/src/js/post_platform_accounts.js',
            'cyllo_social_media_marketing/static/src/xml/post_platform_accounts.xml',
            'cyllo_social_media_marketing/static/src/js/mode_radio_field.js',
            'cyllo_social_media_marketing/static/src/xml/mode_radio_field.xml',
            'cyllo_social_media_marketing/static/src/js/media_upload_field.js',
            'cyllo_social_media_marketing/static/src/scss/platform_tile_toggle.scss',
            'cyllo_social_media_marketing/static/src/js/streams/stream_registry.js',
            'cyllo_social_media_marketing/static/src/js/streams/board_form_dialog.js',
            'cyllo_social_media_marketing/static/src/js/streams/board_sidebar.js',
            'cyllo_social_media_marketing/static/src/js/streams/instagram_embed_dialog.js',
            'cyllo_social_media_marketing/static/src/js/streams/share_dialog.js',
            'cyllo_social_media_marketing/static/src/js/streams/stream_column.js',
            'cyllo_social_media_marketing/static/src/js/streams/add_stream_panel.js',
            'cyllo_social_media_marketing/static/src/js/streams/streams_board.js',
            'cyllo_social_media_marketing/static/src/xml/streams/board_sidebar.xml',
            'cyllo_social_media_marketing/static/src/xml/streams/board_form_dialog.xml',
            'cyllo_social_media_marketing/static/src/xml/streams/instagram_embed_dialog.xml',
            'cyllo_social_media_marketing/static/src/xml/streams/share_dialog.xml',
            'cyllo_social_media_marketing/static/src/xml/streams/stream_column.xml',
            'cyllo_social_media_marketing/static/src/xml/streams/add_stream_panel.xml',
            'cyllo_social_media_marketing/static/src/xml/streams/streams_board.xml',
            'cyllo_social_media_marketing/static/src/scss/streams_board.scss',
            'cyllo_social_media_marketing/static/src/js/platform_registry.js',
            'cyllo_social_media_marketing/static/src/js/platform_picker_dialog.js',
            'cyllo_social_media_marketing/static/src/js/connect_account_dialog.js',
            'cyllo_social_media_marketing/static/src/js/social_media_dashboard.js',
            'cyllo_social_media_marketing/static/src/js/social_media_post_calendar.js',
            'cyllo_social_media_marketing/static/src/xml/calendar_event_card.xml',
            'cyllo_social_media_marketing/static/src/xml/calendar_popover.xml',
            'cyllo_social_media_marketing/static/src/scss/calendar_event_card.scss',
            'cyllo_social_media_marketing/static/src/xml/platform_picker_dialog.xml',
            'cyllo_social_media_marketing/static/src/xml/connect_account_dialog.xml',
            'cyllo_social_media_marketing/static/src/xml/social_media_dashboard.xml',
            'cyllo_social_media_marketing/static/src/scss/social_media_dashboard.scss',
            'cyllo_social_media_marketing/static/src/js/chatter.js',
            'cyllo_social_media_marketing/static/src/js/chatter_container.js',
            'cyllo_social_media_marketing/static/src/js/chatter_action.js',
            'cyllo_social_media_marketing/static/src/scss/kanban.scss',
            'cyllo_social_media_marketing/static/src/css/feed_kanban.css',
        ],
    },
    'images': [
    ],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': True ,
}
