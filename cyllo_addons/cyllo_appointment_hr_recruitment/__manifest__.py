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
    'name': 'Cyllo Appointment - Recruitment Tracking',
    'category': 'Services/Appointments',
    'summary': 'Keep track of recruitment appointments with Cyllo Appointment',
    'description': """
Cyllo Appointment HR Recruitment
=================================
Integrates the Cyllo Recruitment module (hr_recruitment) with the
Cyllo Appointment module (cyllo_appointment).

Features:
- Links appointments to HR applicants via a unique interview invite code
- Adds an "applicant_code" parameter to appointment booking URLs so
  that booked appointments are automatically associated with the
  correct applicant record
- Provides a one-click email template that sends a personalised
  scheduling link to the applicant
    """,
    'version': "1.0",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': [
        'cyllo_appointment',
        'hr_recruitment',
    ],
    'auto_install': False,
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'data': [
        'security/security.xml',
        'data/mail_template_data.xml',
        'data/cyllo_appointment_hr_recruitment_data.xml',
        'views/hr_applicant_views.xml',
        'views/website_appointment_templates.xml',
    ],
}
