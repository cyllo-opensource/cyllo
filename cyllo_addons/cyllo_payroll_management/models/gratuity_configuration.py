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


class GratuityConfiguration(models.Model):
    """To create gratuity configuration for the employee"""
    _name = 'gratuity.configuration'
    _description = 'Gratuity Configuration'

    name = fields.Char(help='To add the name of the configuration', required=True, copy=False, default='New')
    contract_type = fields.Selection([('limited', 'Limited'), ('open', 'Open')],
                                     required=True,
                                     help='Type of employee contract\n'
                                          'Limited: applied when there is an end date for employee contract\n'
                                          'Unlimited: applied when there is no end date for employee contract')
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    start_date = fields.Date(help='Start date of gratuity')
    end_date = fields.Date(help='End date of gratuity')
    date_from = fields.Selection([('first','First contract'),('current','Current contract'),('exact','Exact contract period'),('manual','Manual')],
                                 help="The employee experience will be calculated from \n"
                                      "First contract: The start date of the first contract of employee\n"
                                      "Current contract: The start date of the current contract of the employee\n"
                                      "Exact contract period: The exact period of time the employee is in any contract\n"
                                      "Manual: You can choose the date manually", default = 'first', required=True)
    joining_date = fields.Date(string="Joining date", help="This date will be used for the gratuity of the employee")
    include_training = fields.Boolean(string="Include training", help="If enabled, the training period of employee also included in gratuity computation")
    active = fields.Boolean(default=True)
    gratuity_configuration_ids = fields.One2many('gratuity.configuration.line',
                                                 'gratuity_configuration_id', help='Gratuity configuration lines')

    _sql_constraints = [('unique_name', "unique(name)", "The name must be unique")]

    @api.onchange('start_date', 'end_date')
    def _onchange_start_date(self):
        """ Function to check date if it is added correct or not"""
        if self.start_date and self.end_date and not self.start_date < self.end_date:
            raise ValidationError(_("End date must be grater than the start date "))


class GratuityConfigurationLine(models.Model):
    """To create gratuity configuration for the employee"""
    _name = 'gratuity.configuration.line'
    _description = 'Gratuity Configuration Line'
    _sql_constraints = [
        ('unique_name', "unique(name)", "The name must be unique")]

    name = fields.Char(required=True)
    from_year = fields.Float(
        help="This rule will be applicable when employee's experience id more than this number of years.\n"
             "If set to 0 then only the end year will be considered.")
    to_year = fields.Float(
        help="This rule will be applicable when an employee's experience is less than this number of years.\n"
             "If set to 0, then only the start year will be considered.")
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    divide_days = fields.Integer(default=30, string="Divide days",
                                 help="The employee basic salary will be divided by this no. of days for gratuity computation\n"
                                      "e.g. if the given number is 30, then the value will be basic salary/30")
    extra_days = fields.Integer(default=21, help='Number of extra working days allowed per year', string="Extra days")
    percentage = fields.Float(default=100, help='The total amount will be calculated with the percentage given here',
                              string="Percentage")
    gratuity_configuration_id = fields.Many2one('gratuity.configuration', readonly=True)

    @api.onchange('from_year', 'to_year')
    def _onchange_from_year(self):
        """ The onchange function is used to check, the year is configured correctly or not """
        if self.from_year and self.to_year and not self.from_year < self.to_year:
            raise ValidationError(_("'From Year' should be less than 'To Year'."))

    @api.constrains('divide_days', 'extra_days', 'percentage')
    def _constrain_divide_days(self):
        """Validation for days and percentage for preventing conflict while
        calculating gratuity amount"""
        for rec in self:
            if rec.divide_days <= 0 or rec.extra_days <= 0 or rec.percentage <= 0:
                raise ValidationError("Divide days,extra days and percentage must be greater than 0")
