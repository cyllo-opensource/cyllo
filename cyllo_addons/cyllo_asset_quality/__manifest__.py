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
    'name': 'Cyllo Asset Quality',
    'summary': 'Integration between Cyllo Asset Management and Cyllo Quality',
    'description': """
        This module integrates asset management with quality checks.
        Allows performing quality checks before returning leased or rented assets.
        Automatically creates maintenance requests if quality checks fail.
    """,
    'version': "1.0",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'category': 'Accounting',
    'depends': [
        'cyllo_asset_management',
        'cyllo_quality'
    ],
    'data': [
        'security/security.xml',
        'views/quality_control_point_views.xml',
        'views/quality_check_views.xml',
        'views/asset_lease_views.xml',
        'views/asset_rental_views.xml',
        'views/asset_item_views.xml',
        'views/asset_asset_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
