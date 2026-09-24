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
    'name': 'Cyllo Email Digitization',
    'category': 'Extra Tools',
    'summary': """Digitize Emails Automatically.""",
    'description': """This module helps to retrieve data from email and 
     generate the field values of sale and purchase automatically.""",
    'version': "1.0",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': [
        'sale_management', 'purchase', 'mail', 'cyllo_ocr_digitization'
    ],
    'icon': '/cyllo_email_digitization/static/description/email-digitalization.svg',
    'data': [
        'security/email_digitization_security.xml',
        'security/ir.model.access.csv',
        'data/mail_template_data.xml',
        'views/email_digitization_config_views.xml',
        'views/email_digitization_data_views.xml',
    ],
    'external_dependencies': {
        'python': ['beautifulsoup4', 'validate_email', 'py3DNS']
    },
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
