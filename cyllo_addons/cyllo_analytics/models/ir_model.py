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
from odoo import api, fields, models


class IrModel(models.Model):
    """Model representing various models in the system."""
    _inherit = "ir.model"

    table_name = fields.Char(
        'Table Name',
        help="Name of the field is auto completed using post_init_hook to get the field name for reference")

    @api.model
    def get_model_from_table(self, table):
        """Retrieve the model associated with a given table name."""
        model = self.search([('table_name', '=', table)])
        if model:
            return self.env["dashboard.sheet"].get_data(model.id)
        return {}
