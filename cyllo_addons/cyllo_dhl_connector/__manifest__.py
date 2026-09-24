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
    'name': 'Cyllo DHL Connector',
    'category': 'Sales',
    'summary': 'Integrate DHL shipping services with Cyllo',
    'description': """The DHL Connector module for Cyllo allows you to integrate 
     DHL shipping services into your Cyllo instance.This module simplifies the
     shipping process, making it easier for businesses to use DHL's
     global shipping services while maintaining control and visibility through 
     the Cyllo platform.""",
    'version': "1.0",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['sale_management', 'delivery', 'stock', 'website', 'portal', 'website_sale'],
    'icon': '/cyllo_dhl_connector/static/description/dhl.svg',
    'data': [
        'data/product_product_data.xml',
        'views/delivery_carrier_views.xml',
        'views/res_config_settings_views.xml'
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
