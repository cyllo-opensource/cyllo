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


class HrServiceCategory(models.Model):
    """Class for managing service categories related to employee services."""
    _name = 'hr.service.category'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Service Category"

    name = fields.Char(help="Name of the service category.", required=True)
    description = fields.Html(
        help="Detailed description of the service category.")
    parent_id = fields.Many2one('hr.service.category', string="Parent Category",
                                help="Parent category to which this category belongs.")
    company_id = fields.Many2one('res.company', readonly=True,
                                 default=lambda self: self.env.company,
                                 help="Company associated with the service category.")
    require_maintenance_order = fields.Boolean(
        string="Create Maintenance Order",
        help="If enabled, service requests with this category will generate a maintenance order.")
