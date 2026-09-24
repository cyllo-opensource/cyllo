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


class HrIncidentCategory(models.Model):
    """Model for managing incident categories.
        This model defines categories for incidents, including a name,
        description and the company the category belongs to.
        """
    _name = 'hr.incident.category'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Incident Category"

    name = fields.Char(required=True)
    description = fields.Html(help='Describe the category')
    company_id = fields.Many2one('res.company', readonly=True, default=lambda self: self.env.company)
