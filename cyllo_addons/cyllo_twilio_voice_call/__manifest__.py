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
    'name': 'Cyllo Twilio Voice Call',
    'category': 'Productivity',
    'summary': """Make a voice call using twilio""",
    'description': """The module helps you to make a call using the 
     twilio account.""",
    'version': "1.0",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['contacts', 'web', 'cyllo_web'],
    'icon': '/cyllo_twilio_voice_call/static/description/twillio.svg',
    'data': [
        'security/cyllo_twilio_voice_call_security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'views/incoming_call_list_views.xml',
        'views/res_config_settings_views.xml',
        'views/out_going_call_list_views.xml',
    ],
    'external_dependencies': {
        'python': ['twilio'],
    },
    'assets': {
        'web.assets_backend': [
            'https://cdn.jsdelivr.net/npm/@twilio/voice-sdk@2.0.1/dist/twilio.min.js',
            'cyllo_twilio_voice_call/static/src/xml/twilio_systray_icon.xml',
            'cyllo_twilio_voice_call/static/src/xml/outgoing_call_templates.xml',
            'cyllo_twilio_voice_call/static/src/xml/contact_tab.xml',
            'cyllo_twilio_voice_call/static/src/xml/recent_tab.xml',
            'cyllo_twilio_voice_call/static/src/xml/incoming_call_templates.xml',
            'cyllo_twilio_voice_call/static/src/js/twilio_systray_icon.js',
            'cyllo_twilio_voice_call/static/src/js/outgoing_call.js',
            'cyllo_twilio_voice_call/static/src/js/incoming_call.js',
            'cyllo_twilio_voice_call/static/src/js/recent_tab.js',
            'cyllo_twilio_voice_call/static/src/js/contact_tab.js',
            'cyllo_twilio_voice_call/static/src/css/dial_pad.css',
            'cyllo_twilio_voice_call/static/src/css/remixicon.css',
            'cyllo_twilio_voice_call/static/src/js/navbar.js',
            'cyllo_twilio_voice_call/static/src/xml/navbar.xml',
            'cyllo_twilio_voice_call/static/src/xml/call_form_fields.xml',
            'cyllo_twilio_voice_call/static/src/js/form_phone_field.js',
            'cyllo_twilio_voice_call/static/src/xml/call_option_modal.xml',
            'cyllo_twilio_voice_call/static/src/js/call_option_modal.js',

        ],
    },
    'license': 'LGPL-3',
    'installable': True,
    'application': True,
    'auto_install': False,
}
