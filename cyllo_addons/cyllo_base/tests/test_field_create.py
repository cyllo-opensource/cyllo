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

_LOGGER = logging.getLogger(__name__)


class TestFieldCreate(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        """Super setUpClass to declare records globally"""
        cls.model_id = cls.env['ir.model'].search([
            ('model', '=', 'ir.module.module')
        ])
        cls.field_id = cls.env['ir.model.fields'].search([
            ('name', '=', 'category_id'),
            ('field_description', '=', 'Category'),
            ('model_id', '=', cls.model_id.id),
        ])
        cls.email_widget = cls.env.ref('cyllo_base.field_widget_email')
        cls.create_id = cls.env['field.create'].create({
            'name': 'x_test_field',
            'field_type': 'char',
            'name_x_': True,
            'display_name': 'Test Field',
            'model': cls.model_id.model,
            'field_id': cls.field_id.id,
            'form_view_external_id': 'base.module_form',
            'position': 'after',
            'widget_id': cls.email_widget.id,
            'store': True,
            'copied': True,
            'help': 'This is a test field',
        })

    def test_get_xml_ids(self):
        """Test for the 'get_xml_ids' fn"""
        _LOGGER.info("Starts tests for 'get_xml_ids'")
        self.assertDictEqual(self.create_id.get_xml_ids('ir.module.module'),
                             {'model': 'ir.module.module',
                              'form_external_id': 'base.module_form'})
        _LOGGER.info("End tests for 'get_xml_ids'")

    def test_get_possible_field_types(self):
        """Test for the 'get_possible_field_types' fn and check return
            contains expected list"""
        _LOGGER.info("Starts tests for 'get_possible_field_types'")
        self.assertListEqual(self.create_id.get_possible_field_types(),
                             [('binary', 'binary'), ('boolean', 'boolean'),
                              ('char', 'char'), ('date', 'date'),
                              ('datetime', 'datetime'), ('float', 'float'),
                              ('html', 'html'), ('integer', 'integer'),
                              ('many2many', 'many2many'),
                              ('many2one', 'many2one'),
                              ('many2one_reference', 'many2one_reference'),
                              ('properties', 'properties'), (
                                  'properties_definition',
                                  'properties_definition'),
                              ('selection', 'selection'), ('text', 'text')])
        _LOGGER.info("End tests for 'get_possible_field_types'")

    def test_onchange_name(self):
        """Test '_onchange_name' fn by create a field with same name and
            check boolean field changing correctly """
        _LOGGER.info("Starts tests for '_onchange_name'")
        self.env['ir.model.fields'].create({'name': self.create_id.name,
                                            'model': self.create_id.model,
                                            'model_id': self.model_id.id,
                                            'ttype': 'char'})
        self.create_id._onchange_name()
        self.assertEqual(self.create_id.same_name, True)
        self.assertEqual(self.create_id.name_x_, False)
        _LOGGER.info("End tests for '_onchange_name'")

    def test_action_create_field(self):
        """Test 'action_create_field' fn by checking new field created with
            given datas and tree and form views are created with given
            architecture"""
        _LOGGER.info("Starts tests for 'action_create_field'")
        self.create_id.env.context = {'active_model': 'ir.module.module',
                                      'default_form_view_external_id':
                                          'base.module_form',
                                      'default_model': 'ir.module.module',
                                      'lang': 'en_US', 'tz': 'Asia/Calcutta',
                                      'uid': 2, 'allowed_company_ids': [1]}
        res = self.create_id.action_create_field()
        new_field = self.env['ir.model.fields'].search([
            ('name', '=', self.create_id.name),
            ('model', '=', self.create_id.model),
            ('model_id', '=', self.model_id.id),
            ('ttype', '=', 'char')
        ])
        form_view_id = self.env['ir.ui.view'].search([
            ('name', '=', 'ir.module.module' + ".form." + "add.field." +
             self.create_id.name),
            ('model', '=', 'ir.module.module'),
            ('mode', '=', 'extension')
        ])
        self.assertDictEqual(res, {'type': 'ir.actions.client',
                                   'tag': 'reload', 'form_view_id': 95})
        self.assertEqual(new_field.name, self.create_id.name)
        self.assertEqual(new_field.model, self.create_id.model)
        self.assertEqual(new_field.model_id, self.model_id)
        self.assertEqual(form_view_id.arch_base,
                         ('<?xml version="1.0"?>'
                          '<data>'
                          '''<field name="%s" position="%s">'''
                          '''<field name="%s" widget="%s"/>'''
                          '''</field>'''
                          '''</data>''') % (self.create_id.field_id.name,
                                            self.create_id.position,
                                            self.create_id.name,
                                            self.create_id.widget_id.name))
        self.assertEqual(self.env['ir.ui.view'].search([
            ('name', '=', 'ir.module.module' + ".tree." + "add.field." +
             self.create_id.name)]).arch_base,
                         ('<?xml version="1.0"?>'
                          '''<data>'''
                          '''<xpath expr="//tree" position="inside">'''
                          '''<field name="%s" optional="hide"/>'''
                          '''</xpath>'''
                          '''</data>''') % self.create_id.name)
        _LOGGER.info("End tests for 'action_create_field'")
