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
    'name': "Cyllo Planning",
    'category': 'Human Resources',
    'summary': 'Planning Module for Cyllo ERP',
    'description': """The Planning Module in Cyllo ERP provides a versatile 
        solution for optimizing organizational planning and resource 
        allocation. Featuring an intuitive interface and robust Gantt view 
        functionality, users can effortlessly create, modify, and visualize 
        plans with precision. This module simplifies task and resource 
        allocation, empowering managers to boost productivity and monitor 
        timelines effectively. Leveraging the Planning module enables 
        organizations to streamline planning workflows, enhance operational 
        efficiency, and achieve better outcomes across various initiatives 
        within the Cyllo ERP.""",
    'version': "1.0",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['cyllo_hr','hr_holidays'],
    'icon': '/cyllo_planning/static/description/planning.svg',
    'data': [
        'security/cyllo_planning_security.xml',
        'security/ir.model.access.csv',
        'views/plan_allocation_views.xml',
        'views/allocation_type_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'cyllo_planning/static/src/js/planning_calendar.js',
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': True,
}
