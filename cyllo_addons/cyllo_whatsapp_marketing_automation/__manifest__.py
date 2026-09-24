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
    'name': 'Cyllo Whatsapp Marketing Automation',
    'category': 'Marketing',
    'summary': "Automate WhatsApp marketing campaigns and activity-based messaging in Odoo.",
    'description': """WhatsApp Marketing Automation enables businesses to automate marketing communications through WhatsApp directly from Odoo. 
     It allows triggering messages based on marketing activities, customer interactions, and predefined workflows, helping improve engagement, follow-ups, and campaign efficiency while reducing manual effort.""",
    'version': "1.0",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['cyllo_whatsapp', 'cyllo_marketing_automation'],
    'data': [
        'views/marketing_activity_views.xml',
        
    ],
    'assets': {
        'web.assets_backend': [
            'cyllo_whatsapp_marketing_automation/static/src/xml/marketing_activity_childs.xml',
            'cyllo_whatsapp_marketing_automation/static/src/js/activity_recursive_component.js',
        ],
    },
    'images': [
    ],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
