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
from datetime import date

from odoo import Command
from odoo.tests import common


class TestCylloFieldService(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.currency = cls.env['res.currency'].create({
            'name': 'Gold Coin',
            'symbol': '☺',
            'rounding': 0.001,
            'position': 'after',
            'currency_unit_label': 'Gold',
            'currency_subunit_label': 'Silver',
        })
        cls.partner = cls.env['res.partner'].create({
            'name': 'Partner',
        })
        cls.user = cls.env['res.users'].create({
            'name': 'User',
            'login': 'test_user_field_service',
        })
        cls.company = cls.env['res.company'].create({
            'name': 'Test Company'
        })
        cls.skill_type = cls.env['hr.skill.type'].create({
            'name': 'Skill Type 1'
        })
        cls.hr_skill = cls.env['hr.skill'].create({
            'name': 'Test skill',
            'skill_type_id': cls.skill_type.id,
        })
        cls.hr_skill_2 = cls.env['hr.skill'].create({
            'name': 'Skill 2',
            'skill_type_id': cls.skill_type.id
        })
        cls.hr_skill_3 = cls.env['hr.skill'].create({
            'name': 'Skill 3',
            'skill_type_id': cls.skill_type.id
        })
        cls.skill_category = cls.env['field.service.skill.category'].create({
            'name': 'Category',
            'company_id': cls.company.id,
            'hr_skill_ids': cls.hr_skill.ids,
        })
        cls.skill_level = cls.env['hr.skill.level'].create({
            'name': 'Level 1',
            'skill_type_id': cls.skill_type.id,
            'level_progress': 25,
        })
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Employee 1',
            'employee_skill_ids': [(0, 0, {
                'skill_id': cls.hr_skill.id,
                'skill_type_id': cls.skill_type.id,
                'skill_level_id': cls.skill_level.id,
            })],
        })
        cls.employee_2 = cls.env['hr.employee'].create({
            'name': 'Employee 2',
            'employee_skill_ids': [(0, 0, {
                'skill_id': cls.hr_skill_2.id,
                'skill_type_id': cls.skill_type.id,
                'skill_level_id': cls.skill_level.id,
            })],
        })
        cls.service_request = cls.env['field.service.request'].create({
            'name': 'FS00001',
            'partner_id': cls.partner.id,
            'user_id': cls.user.id,
            'skill_category_id': cls.skill_category.id,
            'state': 'draft',
            'submit_date': '2023-11-30',
        })
        cls.field_service_worker = cls.env['field.service.worker'].create({
            'field_service_request_id': cls.service_request.id,
            'employee_id': cls.employee.id
        })
        cls.service_request_1 = cls.env['field.service.request'].create({
            'name': 'ES00002',
            'partner_id': cls.partner.id,
            'user_id': cls.user.id,
            'skill_category_id': cls.skill_category.id,
            'state': 'draft',
            'submit_date': '2023-11-30',
        })
        cls.product = cls.env['product.product'].create({
            'name': 'Test product',
            'lst_price': 50,
        })
        cls.product2 = cls.env['product.product'].create({
            'name': 'Test product 2',
            'lst_price': 50,
        })
        cls.checklist = cls.env['field.service.checklist'].create({
            'status': 'pending',
            'required': True,
            'service_cost': 100,
            'time_required': 2.0,
            'field_service_request_id': cls.service_request.id,
            'product_id': cls.product.id
        })
        cls.service_request2 = cls.env['field.service.request'].create({
            'name': 'FS00002',
            'partner_id': cls.partner.id,
            'user_id': cls.user.id,
            'skill_category_id': cls.skill_category.id,
            'state': 'submit',
            'submit_date': '2023-11-30',
        })
        cls.checklist_for_req2 = cls.env['field.service.checklist'].create({
            'status': 'pending',
            'required': True,
            'service_cost': 100,
            'time_required': 2.0,
            'field_service_request_id': cls.service_request2.id,
            'product_id': cls.product.id
        })
        cls.checklist2 = cls.env['field.service.checklist'].create({
            'status': 'completed',
            'required': True,
            'service_cost': 100,
            'product_id': cls.product.id
        })
        cls.account_move = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': cls.partner.id,
            'invoice_date': date.today(),
            'invoice_origin': 'FS00003',
            'invoice_line_ids': [Command.create({
                'name': "Field Service",
                'quantity': 1,
                'price_unit': 100,
            })]
        })
        cls.service_request3 = cls.env['field.service.request'].create({
            'name': 'FS00003',
            'partner_id': cls.partner.id,
            'user_id': cls.user.id,
            'skill_category_id': cls.skill_category.id,
            'state': 'submit',
            'submit_date': '2023-11-30',
            'move_ids': [(4, cls.account_move.id)],
        })
        cls.service_request4 = cls.env['field.service.request'].create({
            'name': 'FS00004',
            'partner_id': cls.partner.id,
            'user_id': cls.user.id,
            'skill_category_id': cls.skill_category.id,
            'state': 'in_progress',
            'submit_date': '2023-11-30',
            'move_ids': [(4, cls.account_move.id)],
        })
