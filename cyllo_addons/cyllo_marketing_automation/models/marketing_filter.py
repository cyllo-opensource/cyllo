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
from ast import literal_eval
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class MarketingFilter(models.Model):
    """
        This model is used to define filter domains that can be applied to
        marketing campaigns to target specific groups of participants based on
        certain conditions in the associated target models.
    """
    _name = "marketing.filter"
    _description = "Marketing Filter"
    _inherit = 'mail.thread'

    name = fields.Char(string="Filter Name", help="Enter a name for the filter", required=True)
    user_id = fields.Many2one('res.users', string="Created By", default=lambda self: self.env.user,
                              readonly=True, help='Responsible user ')
    model_id = fields.Many2one('ir.model', string="Target Model", ondelete='cascade',
                               help='Choose target model to filter records')
    model_name = fields.Char(related='model_id.model', store=True, help='Model Name')
    domain = fields.Char(help='Domain to filter the records')
    company_id = fields.Many2one('res.company',
                                 required=True,
                                 default=lambda self: self.env.company)

    @api.constrains('domain', 'model_id')
    def _check_domain(self):
        """ Check that if the mailing domain is set, it is a valid one """
        for filters in self:
            if filters.domain != "[]":
                try:
                    self.env[filters.model_id.model].search_count(literal_eval(filters.domain))
                except:
                    raise ValidationError(_("The domain rule cannot be empty or invalid for the selected target model."))
