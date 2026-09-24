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
    'name': 'Cyllo Product Lifecycle Management (PLM)',
    'category': 'Manufacturing',
    'summary': 'Manage product lifecycle changes through Engineering Change Orders (ECO)',
    'description': """
        Product Lifecycle Management (PLM) Core Foundation:
        - Engineering Change Orders (ECO) workflow.
        - ECO Types (Product and BoM).
        - Stage progression (New, In Progress, Effective).
        - Version control tracking on Bills of Materials and Products.
        - Integration with Manufacturing.
        - BoM comparison structure placeholder.
            """,
    'version': "1.0",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': [
        'mrp',
        'mail',
        'product',
        'cyllo_documents',
    ],
    'icon': '/cyllo_plm/static/description/plm_icon.svg',
    'data': [
        'security/cyllo_plm_security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/plm_eco_type_data.xml',
        'data/plm_eco_stage_data.xml',
        'data/document_workspace_data.xml',
        'views/plm_master_data_actions.xml',
        'views/document_file_views.xml',
        'views/plm_eco_type_views.xml',
        'views/plm_eco_stage_views.xml',
        'views/plm_eco_views.xml',
        'views/mrp_bom_views.xml',
        'views/product_template_views.xml',
        'views/plm_menus.xml',
        'wizards/plm_eco_compare_wizard_views.xml'
    ],
    'demo': [
        'demo/plm_eco_demo.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': True,
}
