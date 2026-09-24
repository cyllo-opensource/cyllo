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
import random
from odoo import fields, models


class AllocationType(models.Model):
    """Represents planning allocation type."""
    _name = 'allocation.type'
    _description = "Planning Allocation Type"

    name = fields.Char(required=True)
    color = fields.Char(help="Choose color for allocation", default=lambda self: self._default_color())
    description = fields.Text(help="Allocation type description")
    user_id = fields.Many2one('res.users', required=True, default=lambda self: self.env.user, string="Created By")
    company_id = fields.Many2one('res.company', required=True,
                                 default=lambda self: self.env.company)

    def _default_color(self):
        """Function to get random color for allocation type"""
        return '#{:06x}'.format(random.randint(0, 0xFFFFFF))
