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
    'name': 'Cyllo Project In Field Service',
    'category': 'Sales',
    'summary': """Enhance field service management with integrated project functionality""",
    'description': "The Project In Field Service module integrates project management features into Cyllo Field "
                   "Service, allowing you to seamlessly handle projects alongside service requests. Track project "
                   "tasks, manage resources, and streamline invoicing, all within your field service environment. "
                   "Improve efficiency and coordination across your organization with Project In Field Service.",
    'version': "1.0",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['cyllo_field_service', 'project', 'hr_timesheet', 'sale_project'],
    'data': [
        'security/ir.model.access.csv',
        'data/project_data.xml',
        'views/project_task_views.xml',
        'views/field_service_request_views.xml',
        'views/project_project_views.xml',
        'wizards/field_service_invoice_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
