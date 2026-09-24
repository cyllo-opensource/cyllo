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
    "name": "Cyllo AI",
    "summary": "ERP Analytics Chatbot",
    "description": "Adds an AI chatbot that answers business questions in "
                   "natural language, running read-only queries and confirmed "
                   "record updates through a tool-based agent loop on the "
                   "configured LLM.",
    'version': "1.0",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    "category": "Extra Tools",
    "depends": ['web', 'sale', 'cyllo_web'],
    'icon': '/cyllo_ai/static/description/ai.svg',
    'post_init_hook': 'post_init_hook',
    "data": [
            'security/cyllo_ai_security.xml',
            'security/ir.model.access.csv',
            'data/cyllo_llm_data.xml',
            'data/chatbot_session_data.xml',
            'views/cyllo_ai_config_views.xml',
            'views/cyllo_ai_views.xml',
            'views/cyllo_ai_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'https://unpkg.com/lottie-web/build/player/lottie.min.js',
            'cyllo_ai/static/src/lib/marked/marked.min.js',
            'cyllo_ai/static/src/chat_sidebar/chat_sidebar.js',
            'cyllo_ai/static/src/chat_sidebar/chat_sidebar.xml',
            'cyllo_ai/static/src/chat_sidebar/chat_sidebar.css',
            'cyllo_ai/static/src/chat_response/chat_response.js',
            'cyllo_ai/static/src/chat_response/chat_response.xml',
            'cyllo_ai/static/src/chat_response/chat_response.css',
            'cyllo_ai/static/src/chat_user/chat_user.js',
            'cyllo_ai/static/src/chat_user/chat_user.xml',
            'cyllo_ai/static/src/chat_user/chat_user.css',
            'cyllo_ai/static/src/chatbot/chatbot.js',
            'cyllo_ai/static/src/chatbot/chatbot.css',
            'cyllo_ai/static/src/chatbot/chatbot_templates.xml',
            'cyllo_ai/static/src/chatbot_screen/chatbot_screen.js',
            'cyllo_ai/static/src/chatbot_screen/chatbot_screen.css',
            'cyllo_ai/static/src/chatbot_screen/chatbot_screen.xml',
        ],
    },
    'license': 'LGPL-3',
    "installable": True,
    "application": True,
    "auto_install": False
}
