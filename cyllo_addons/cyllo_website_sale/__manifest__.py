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
    'name': "Cyllo Ecommerce",
    'summary': "Debranding default brand and replaces with Cyllo",
    'description': """This module helps to removes any pre-existing branding and replaces it with "Cyllo" as the new brand.""",
    'version': "1.0",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'data': ['views/templates.xml'],
    'assets': {
        'website.backend_assets_all_wysiwyg': [
            ('remove', 'website_sale/static/src/js/components/wysiwyg_adapter/wysiwyg_adapter.js'),
            'cyllo_website_sale/static/src/js/wysiwyg_adapter.js'
        ],
        'website.assets_editor': [
            'cyllo_website_sale/static/src/js/editor.js'
        ],
    },
    'depends': ['cyllo_base', 'website_sale'],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': True
}
