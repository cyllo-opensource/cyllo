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
from odoo.tests import TransactionCase


class TestFieldServiceRequestPrint(TransactionCase):
    """Test report values for field service request"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Partner',
        })
        cls.company = cls.env['res.company'].create({
            'name': 'Test Company'
        })
        cls.skill_type = cls.env['hr.skill.type'].create({
            'name': 'Skill Type 1'
        })
        cls.skill = cls.env['hr.skill'].create({
            'name': 'Test skill',
            'skill_type_id': cls.skill_type.id,
        })
        cls.skill_category = cls.env['field.service.skill.category'].create({
            'name': 'Category',
            'company_id': cls.company.id,
            'hr_skill_ids': cls.skill.ids,
        })
        cls.fs_request = cls.env['field.service.request'].create({
            'name': 'FS00001',
            'partner_id': cls.partner.id,
            'skill_category_id': cls.skill_category.id,
            'state': 'draft',
            'submit_date': '2023-11-30',
            'hr_skill_ids': cls.skill_category.ids,
        })
        move_1 = cls.env['account.move'].create({
            'partner_id': cls.partner.id,
            'move_type': 'out_invoice',
            'invoice_line_ids': [(0, 0, {
                'name': 'Test Product',
                'quantity': 1,
                'price_unit': 100,
            })],
        })
        move_1.action_post()
        move_2 = cls.env['account.move'].create({
            'partner_id': cls.partner.id,
            'move_type': 'out_invoice',
            'invoice_line_ids': [(0, 0, {
                'name': 'Service 2',
                'quantity': 1,
                'price_unit': 200,
            })]
        })
        move_2.action_post()
        cls.fs_request.write({'move_ids': [(6, 0, [move_1.id, move_2.id])]})
        move_1.amount_residual = 0.0
        move_2.amount_residual = 50.0

    def test_get_report_values_print(self):
        """Test _get_report_values() returns correct calculations"""
        report_model = self.env['report.cyllo_field_service.report_field_service_request_form']
        result = report_model._get_report_values([self.fs_request.id])
        total_amount = 300.0
        paid_amount = 250.0
        balance = 50.0
        self.assertEqual(result['amount'], total_amount)
        self.assertEqual(result['paid_amount'], paid_amount)
        self.assertEqual(result['balance_amount'], balance)
        self.assertEqual(result['fs_request'], self.fs_request)
