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
from odoo import fields, models


class FieldServiceSkillCategory(models.Model):
    """In this class we are defining the fields required for model field.service.skill.category"""
    _name = "field.service.skill.category"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Field Service Skill Category"

    name = fields.Char(required=True, help="Name of category")
    description = fields.Text(help="Description about the category")
    hr_skill_ids = fields.Many2many('hr.skill', string="Skills",
                                    help="Skills in the category")
    parent_id = fields.Many2one("field.service.skill.category",
                                string="Parent Category",
                                help="Parent category")
    company_id = fields.Many2one('res.company', required=True,
                                 default=lambda self: self.env.company,
                                 help="Company name")
    service_checklist_ids = fields.One2many("field.service.skill.category.line",
                                            'skill_category_id',
                                            string="Service Checklists",
                                            help="Service request checklists")

