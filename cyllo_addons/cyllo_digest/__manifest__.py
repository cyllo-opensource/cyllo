# -*- coding: utf-8 -*-
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
