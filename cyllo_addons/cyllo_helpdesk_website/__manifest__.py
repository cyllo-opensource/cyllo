# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cyllo(<https://www.cyllo.com>)
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
    'name': 'Cyllo Helpdesk Website',
    'category': 'Services/Helpdesk',
    'summary': """Website integration for Cyllo Help Desk""",
    'description': "Integrates Cyllo Helpdesk with Website to allow users to create helpdesk tickets directly from website forms.",
    'version': "1.0",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['cyllo_helpdesk', 'website'],
    'data': [
        'data/website_form_data.xml',
    ],
    'assets': {
        'website.assets_wysiwyg': [
            'cyllo_helpdesk_website/static/src/js/website_helpdesk_editor.js',
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
}
