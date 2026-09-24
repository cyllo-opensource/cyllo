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
    'name': "Cyllo Database Backup Management",
    'summary': """Generate automatic backup of databases and store to local,
     google drive, dropbox, nextcloud, amazon S3, onedrive or remote server""",
    'description': """This module has been developed for creating database 
     backups automatically and store it to the different locations.""",
    'version': "1.0",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'category': 'Extra Tools',
    'depends': ['mail'],
    'icon': '/cyllo_database_backup/static/description/database-backup.svg',
    'data': [
        'security/ir.model.access.csv',
        'data/backup_destination_data.xml',
        'data/ir_cron_data.xml',
        'data/mail_template_data.xml',
        'data/discuss_channel_data.xml',
        'wizards/dropbox_auth_code.xml',
        'views/db_backup_configure_views.xml',
        'views/backup_destination_views.xml',
    ],
    'external_dependencies': {
        'python': ['nc_py_api','dropbox', 'pyncclient', 'boto3','paramiko']},
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
