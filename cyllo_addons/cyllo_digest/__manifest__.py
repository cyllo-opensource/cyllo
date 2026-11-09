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
    'name': 'Cyllo Digest',
    'category': 'Productivity',
    'summary': 'Cyllo branding for the periodic digest email',
    'description': """
        Removes the Odoo mobile banner and Odoo naming from the periodic
        digest email without modifying the base digest module.
    """,
    'author': 'Cyllo',
    'website': 'https://www.cyllo.com',
    'depends': ['digest'],
    'data': [
        'views/digest_templates.xml',
        'data/digest_data.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
}
