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
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class EmployeeSalaryStructure(models.Model):
    """The class is used to manage and create the salary """
    _name = 'employee.salary.structure'
    _description = 'Salary Structure'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    @api.model
    def _get_parent(self):
        """ This method is used to retrieve the parent record representing the base payroll structure. """
        default_structure = self.env.ref(
            'cyllo_payroll_management.employee_salary_structure_base_for_new_structures',
            False)
        return default_structure if default_structure and default_structure.sudo().company_id.id in self.env.company.ids else False

    @api.model
    def _get_default_rule_ids(self):
        rule_ids = []
        for xml_id in [
            'cyllo_payroll_management.employee_salary_rule_basic_salary',
            'cyllo_payroll_management.employee_salary_rule_gross',
            'cyllo_payroll_management.employee_salary_rule_attachment_of_salary',
            'cyllo_payroll_management.employee_salary_rule_assignment_of_salary',
            'cyllo_payroll_management.employee_salary_rule_child_support',
            'cyllo_payroll_management.employee_salary_rule_net_salary',
        ]:
            rule = self.env.ref(xml_id, raise_if_not_found=False)
            if rule:
                rule_ids.append(rule.id)
        return [(6, 0, rule_ids)]

    name = fields.Char(required=True, help='The name of the record.')
    code = fields.Char(string='Reference', required=True, help='A unique reference code for the record.')
    type_id = fields.Many2one('hr.payroll.structure.type', required=True, ondelete='restrict',
                              help='The type of this salary structure')
    schedule_pay = fields.Selection(related='type_id.default_schedule_pay', help='Scheduled payment type')
    company_id = fields.Many2one('res.company', copy=False,
                                 default=lambda self: self.env.company.id,
                                 help='The company associated with this record')
    country_id = fields.Many2one('res.country', help='To choose the country',
                                 default=lambda self: self.env.company.country_id)
    note = fields.Text(string='Description', help='Additional description or notes related to the record')
    parent_id = fields.Many2one('employee.salary.structure',
                                help='The parent payroll structure for this record.', default=_get_parent,
                                domain="[('id', '!=', id)]")
    children_ids = fields.One2many('employee.salary.structure', 'parent_id', copy=True,
                                   help='The child payroll structures associated with this record.')
    employee_salary_rule_ids = fields.Many2many('employee.salary.rule', 'structure_id',
                                                'rule_id', string='Salary Rules', ondelete='restrict',
                                                default=_get_default_rule_ids,
                                                help='The salary rules associated with this payroll structure.')
    journal_id = fields.Many2one('account.journal', 'Salary Journal', company_dependent=True,
                                 default=lambda self: self.env['account.journal'].sudo().search([
                                     ('type', '=', 'general'), ('company_id', '=', self.env.company.id)], limit=1),
                                 ondelete='restrict', help='The journal of payslip where the journal entry posted')
    other_input_line_type_ids = fields.Many2many('employee.payslip.other.input', string='Other Input Line',
                                                 help='The other input types')
    unpaid_work_entry_type_ids = fields.Many2many('hr.work.entry.type',
                                                  'hr_payroll_structure_hr_work_entry_type_rel',
                                                  string='Unpaid Work Entry Types',
                                                  help='The unpaid work entry types are added here')

    @api.constrains('parent_id')
    def _check_parent_id(self):
        """Check for recursive salary structures"""
        if not self._check_recursion():
            raise ValidationError(_('You cannot create a recursive salary structure.'))

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        """Create a copy of the current payroll structure"""
        self.ensure_one()
        default = dict(default or {}, code=_("%s (copy)") % self.code)
        return super(EmployeeSalaryStructure, self).copy(default)

    def _get_all_rules(self):
        """ To get all the rules """
        all_rules = [rule for struct in self for rule in struct.employee_salary_rule_ids._recursive_search_of_rules()]
        return all_rules

    def _get_parent_structure(self):
        """Get the parent structure and the current structure as a combined """
        parent = self.mapped('parent_id')
        if parent:
            parent = parent._get_parent_structure()
        return parent + self
