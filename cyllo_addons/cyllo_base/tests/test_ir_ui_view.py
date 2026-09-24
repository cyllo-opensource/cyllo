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
import logging
from odoo.tests import common
from xml.etree import ElementTree as ET

_LOGGER = logging.getLogger(__name__)


class TestIrUiView(common.TransactionCase):

    def test_edit_xml_field_label(self):
        """Test 'edit_xml_field_label' fn and check field label changing when
            label given in xml as '<label for='field_name' string='field
            string'/>' and in the db."""
        _LOGGER.info("Starts tests for 'edit_xml_field_label'")
        view_id = self.env['ir.ui.view'].search([('name', '=', 'Apps Kanban')])
        fields = (self.env['ir.model.fields'].
                  search([('name', '=', 'application'),
                          ('model', '=', 'ir.module.module')], limit=1))
        view_id.edit_xml_field_label('ir.module.module', 'kanban', 'Application'
                                     , 'application', 'Test Application')
        self.assertEqual(fields.field_description, 'Test Application')
        # Parse the XML string
        root = ET.fromstring(view_id.arch)
        # Find the position of the "application" field
        application_index = None
        for i, child in enumerate(root):
            if child.tag == 'field' and child.get('name') == 'application':
                application_index = i
        # Insert a <label> element before the "application" field
        if application_index is not None:
            label_element = ET.Element('label',
                                       attrib={'for': 'application',
                                               'string': 'Application'})
            root.insert(application_index, label_element)
        # Convert the modified XML structure back to a string
        view_id.arch = ET.tostring(root, encoding='unicode')
        view_id.edit_xml_field_label('ir.module.module', 'kanban', 'Application'
                                     , 'application', 'New Test Application')
        label_string = ''
        for element in ET.fromstring(view_id.arch).iter():
            if element.tag == 'label' and element.get('for') == 'application':
                label_string = element.get('string')
                break
        self.assertEqual(label_string, 'New Test Application')
        _LOGGER.info("End tests for 'edit_xml_field_label'")
