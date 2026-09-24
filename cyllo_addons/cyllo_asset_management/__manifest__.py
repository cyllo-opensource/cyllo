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
    'name': 'Cyllo Assets Management',
    'category': 'Accounting',
    'summary': """Assets Management""",
    'description': "Adding the functionalities assets on the accounting module",
    'version': "1.0",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': [
        'hr',
        'purchase',
        'hr_maintenance',
        'cyllo_accounting',
    ],
    'icon': '/cyllo_asset_management/static/description/assets.svg',
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/conf_menu_inherit.xml',
        'data/asset_asset_actions_data.xml',
        'data/mail_template_data.xml',
        'data/ir_cron_data.xml',
        'views/asset_asset_views.xml',
        'views/asset_item_views.xml',
        'views/account_move_views.xml',
        'views/account_account_views.xml',
        'views/asset_reservation_views.xml',
        'views/asset_lease_views.xml',
        'views/asset_rental_views.xml',
        'views/asset_assign_views.xml',
        'views/asset_sell_dispose_views.xml',
        'views/asset_asset_insurance_views.xml',
        'views/maintenance_request.xml',
        'views/asset_booking.xml',
        'wizards/asset_modify_views.xml',
        'wizards/assset_insurance_wizard_views.xml',
        'report/asset_report_views.xml',
    ],
    'demo': [
        'demo/asset_demo_data.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': True,
    'auto_install': False,
}
