# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cyllo(<https://www.cyllo.com>)
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


class HelpDeskCategory(models.Model):
    _name = "helpdesk.category"
    _description = "HelpDesk Category"

    name = fields.Char(string="Category", ondelete='restrict',
                       help="Ticket category")
    parent_id = fields.Many2one('helpdesk.category', string="Parent",
                                help="Parent of the category")
    description = fields.Html(string="Description",
                              help="Category description")
    sla_id = fields.Many2one('helpdesk.sla', string="SLA policy id")
