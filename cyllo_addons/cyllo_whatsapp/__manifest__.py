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
    'name': 'Cyllo Whatsapp',
    'category': 'Extra tool',
    'summary': 'Enhance communication with WhatsApp integration for Cyllo ERP.',
    'description': """
        Cyllo Whatsapp is a module for Cyllo ERP, designed to enhance communication capabilities 
        by seamlessly integrating with WhatsApp. This module empowers users to send WhatsApp messages 
        directly from Cyllo ERP, share links via WhatsApp, and integrate WhatsApp functionality 
        into various workflows within the Cyllo ERP platform. With Cyllo Whatsapp, organizations 
        can streamline their communication processes and leverage the popularity and convenience 
        of WhatsApp for business purposes, all within the Cyllo ERP environment.
    """,
    'version': "1.0",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['cyllo_base', 'sale', 'crm'],
    'icon': '/cyllo_whatsapp/static/description/whatsapp.svg',
    'data': [
        'security/ir.model.access.csv',
        'security/cyllo_whatsapp_security.xml',
        'data/whatsapp_template_preview_data.xml',
        'views/res_users_views.xml',
        'wizards/whatsapp_template_message.xml',
        'wizards/whatsapp_template_preview_views.xml',
        'wizards/portal_share_views.xml',
        'views/whatsapp_template_views.xml',
        'views/whatsapp_channel_views.xml',
        'views/whatsapp_menu.xml',
        'views/res_partner_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'https://cdn.jsdelivr.net/npm/opus-media-recorder@latest/OpusMediaRecorder.umd.js',
            'https://cdn.jsdelivr.net/npm/opus-media-recorder@latest/encoderWorker.umd.js',
            'cyllo_whatsapp/static/src/systray/*',
            'cyllo_whatsapp/static/src/chatter/*',
            'cyllo_whatsapp/static/src/css/*',
            'cyllo_whatsapp/static/src/scss/*',
            'cyllo_whatsapp/static/src/xml/*',
            'cyllo_whatsapp/static/src/js/*'
        ]
    },
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
