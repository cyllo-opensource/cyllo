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


class SupportServiceStage(models.Model):
    """ Class defines Support Service Stage model """
    _name = "support.service.stage"
    _description = "Support Service Stage"
    _order = "sequence"

    name = fields.Char(string="Stage", required=True, help="Add more stages")
    sequence = fields.Integer(default=1, help="Order of stage")
    is_closed = fields.Boolean(string="Is Closed Stage",
                               help="Enable if it is closed stage")
    is_canceled = fields.Boolean(string="Is Canceled Stage",
                                 help="Enable if it is canceled stage")
    fold = fields.Boolean(string="Fold", help="Stage folded in kanban")
    company_id = fields.Many2one('res.company', required=True,
                                 default=lambda self: self.env.company,
                                 help="Support service team company")
