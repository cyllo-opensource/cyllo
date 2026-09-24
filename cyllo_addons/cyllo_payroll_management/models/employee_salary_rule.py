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
from odoo.exceptions import UserError, ValidationError
from odoo.tools.safe_eval import safe_eval
from odoo.addons import decimal_precision as decimal


class EmployeeSalaryRule(models.Model):
    """ This class represents the salary rule of the payslip """

    _name = 'employee.salary.rule'
    _order = 'sequence, id'
    _description = 'Employee Salary Rule'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(required=True, translate=True, help='Give a name for the salary rule')
    code = fields.Char(required=True, help="The code of salary rules can be used as reference in computation of "
                                           "other rules. In that case, it is case sensitive.")
    sequence = fields.Integer(required=True, index=True, default=5, help='Use to arrange calculation sequence')
    quantity = fields.Char(default='1.0', help="It is used in computation for percentage and fixed amount. "
                                               "For e.g. A rule for Meal Voucher having fixed amount of 1€ per worked "
                                               "day can have its quantity defined in expression like "
                                               "worked_days.WORK100.number_of_days.")
    category_id = fields.Many2one('employee.salary.rule.category', required=True,
                                  help='Salary rule Category reference')
    parent_category_id = fields.Many2one('employee.salary.rule.category', related='category_id.parent_id', help='Parent category of selected rule category')
    active = fields.Boolean(default=True, help="If the active field is set to false, it will allow you to hide the "
                                               "salary rule without removing it.")
    appears_on_payslip = fields.Boolean(help="Used to display the salary rule on payslip.", default=True)
    parent_rule_id = fields.Many2one('employee.salary.rule', string='Parent Salary Rule', index=True,
                                     help='Mention the parent Salary rule')
    company_id = fields.Many2one('res.company', help='Company', default=lambda self: self.env.company.id)
    condition_select = fields.Selection([('none', 'Always True'), ('range', 'Range'),
                                         ('python', 'Python Expression')], string="Condition Based on", default='none',
                                        required=True, help="Select the condition type for the salary rule.")
    condition_range = fields.Char(string='Range Based on', default='contract.wage',
                                  help='This will be used to compute the % fields values; in general it is on basic,'
                                       'but you can also use categories code fields in lowercase as a variable names'
                                       '(hra, ma, lta, etc.) and the variable basic.')
    condition_python = fields.Text(string='Python Condition', required=True,
                                   default='''
                                   # Available variables:
                                   #----------------------
                                   # payslip: object containing the payslips
                                   # gratuity_settlement_id: payslip field containing gratuity settlement id
                                   # employee: hr.employee object
                                   # contract: hr.contract object
                                   # rules: object containing the rules code (previously computed)
                                   # categories: object containing the computed salary rule categories 
                                   (sum of amount of all rules belonging to that category).
                                   # worked_days: object containing the computed worked days
                                   # inputs: object containing the computed inputs
                                   # Note: returned value have to be set in the variable 'result'
                                   result = rules.NET > categories.NET * 0.10''',
                                   help='Applied this rule for calculation if condition is true. You can specify '
                                        'condition like basic > 1000.')
    condition_range_min = fields.Float(string='Minimum Range', help="The minimum amount, applied for this rule.")
    condition_range_max = fields.Float(string='Maximum Range', help="The maximum amount, applied for this rule.")
    amount_select = fields.Selection([('percentage', 'Percentage (%)'), ('fix', 'Fixed Amount'),
                                      ('code', 'Python Code')], string='Amount Type', index=True, required=True,
                                     default='fix', help="The computation method for the rule amount.")
    amount_fix = fields.Float(string='Fixed Amount', digits=decimal.get_precision('Payroll Fixed Amount'),
                              help="Enter a fixed amount for this payroll element.")
    amount_percentage = fields.Float(string='Percentage (%)', digits=decimal.get_precision('Payroll Percentage'),
                                     help='For example, enter 50.0 to apply a percentage of 50%')
    amount_python_compute = fields.Text(string='Python Code',
                                        default='''
                                        # Available variables:
                                        #----------------------
                                        # payslip: object containing the payslips
                                        # gratuity_settlement_id: payslip field containing gratuity settlement id
                                        # gratuity_amount: gratuity settlement field containing gratuity amount
                                        # employee: hr.employee object
                                        # contract: hr.contract object
                                        # rules: object containing the rules code (previously computed)
                                        # categories: object containing the computed salary rule categories 
                                        (sum of amount of all rules belonging to that  category).
                                        # worked_days: object containing the computed worked days.
                                        # inputs: object containing the computed inputs.
                                        # Note: returned value have to be set in the variable 'result'
                                        result = contract.wage * 0.10''',
                                        help='Enter a valid python code for computation')
    amount_percentage_base = fields.Char(string='Percentage based on', help='result will be affected to a variable')
    child_ids = fields.One2many('employee.salary.rule', 'parent_rule_id',
                                string='Child Salary Rule',
                                help="The list of child salary rules associated with this parent rule.")
    partner_id = fields.Many2one('res.partner',
                                 help="Eventual third party involved in the salary payment of the employees.")
    note = fields.Text(string='Description',
                       help="Enter any additional notes or descriptions related to this record.")
    account_debit_id = fields.Many2one('account.account', string='Debit Account',
                                       help='The debit account for journal entry posted')
    account_credit_id = fields.Many2one('account.account', string='Credit Account',
                                        help='The credit account for journal entry posted')

    @api.constrains('parent_rule_id')
    def _check_parent_rule_id(self):
        """ Check for recursive hierarchy in Salary Rules"""
        if not self._check_recursion(parent='parent_rule_id'):
            raise ValidationError(_('Error! You cannot create recursive hierarchy of Salary Rules.'))

    def _recursive_search_of_rules(self):
        """@return: returns a list of tuple (id, sequence) which are all the children of the passed rule_ids"""
        children_rules = []
        for rule in self.filtered(lambda record: record.child_ids):
            children_rules += rule.child_ids._recursive_search_of_rules()
        return [(rule.id, rule.sequence) for rule in self] + children_rules

    def _compute_rule(self, localdict):
        """The compute function is used to compute the salary rule based on the condition that we have given in the
        rules, it is based on percentage, fixed amount and the python condition."""
        self.ensure_one()
        if self.amount_select == 'fix':
            try:
                return self.amount_fix, float(
                    safe_eval(self.quantity, localdict)), 100.0
            except:
                raise UserError(_('Wrong quantity defined for salary rule %s (%s).') % (self.name, self.code))
        elif self.amount_select == 'percentage':
            try:
                return (float(safe_eval(self.amount_percentage_base, localdict)),
                        float(safe_eval(self.quantity, localdict)), self.amount_percentage)
            except:
                raise UserError(_('Wrong percentage base or quantity defined for salary rule %s (%s).') % (
                    self.name, self.code))
        else:
            try:
                safe_eval(self.amount_python_compute, localdict, mode='exec', nocopy=True)
                return (float(localdict['result']), 'result_qty' in localdict and localdict['result_qty'] or 1.0,
                        'result_rate' in localdict and localdict['result_rate'] or 100.0)
            except:
                raise UserError(_('Wrong python code defined for salary rule %s (%s).') % (self.name, self.code))

    def _satisfy_condition(self, localdict):
        """ The function is used to check the conditions """
        self.ensure_one()
        if self.condition_select == 'none':
            return True
        elif self.condition_select == 'range':
            try:
                result = safe_eval(self.condition_range, localdict)
                return self.condition_range_min <= result <= self.condition_range_max or False
            except:
                raise UserError(_('Wrong range condition defined for salary rule %s (%s).') % (self.name, self.code))
        else:
            try:
                safe_eval(self.condition_python, localdict, mode='exec', nocopy=True)
                return 'result' in localdict and localdict['result'] or False
            except:
                raise UserError(_('Wrong python condition defined for salary rule %s (%s).') % (self.name, self.code))

