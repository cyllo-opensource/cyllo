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
    'name': 'Cyllo Link Tracker',
    'category': 'Marketing',
    'summary': 'QR Code Overview, Record QR Status, and Scan Analytics for Cyllo Link Tracker',
    'description': """
        Provides streamlined QR tracking under the Link Tracker menu:
        1. QR Code Overview — every QR token with Tracked / Not Tracked status.
        2. Record QR Status — global scan analytics per record for all models.
        3. Unscanned QR Tokens — tokens with zero scans across all reports.
    """,
    'version': "1.0",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['link_tracker', 'cyllo_studio'],
    'data': [
        'security/ir.model.access.csv',
        'views/qr_token_views.xml',
        'views/qr_record_status_views.xml',
        'views/link_tracker_menu.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
