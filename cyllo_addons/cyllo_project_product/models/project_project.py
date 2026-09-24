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
from odoo import fields, models, api

class ProjectProject(models.Model):
    _inherit = 'project.project'

    allow_task_products = fields.Boolean(
        string="Products on Tasks",
        help="Track the material used to complete tasks",
        default=False,
    )
    allow_extra_quotations = fields.Boolean(
        string="Extra Quotations",
        help="Create new quotations directly from tasks",
        default=False,
    )

    @api.onchange('allow_task_products', 'allow_extra_quotations')
    def _onchange_allow_task_products(self):
        """Enable project as billable if either the products on task or extra quotation is enabled."""
        if self.allow_task_products or self.allow_extra_quotations:
            self.write({
                'allow_billable' : True,
            })