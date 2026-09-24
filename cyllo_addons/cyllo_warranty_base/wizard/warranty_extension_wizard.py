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


class WarrantyExtensionWizard(models.TransientModel):
    """Base warranty extension wizard.

    Defines the shared fields (extension period/unit) used by both the sale
    and purchase wizard extensions.  Module-specific fields (order references
    and order lines) are added via _inherit in cyllo_warranty_sale and
    cyllo_warranty_purchase respectively.
    """
    _name = 'warranty.extension.wizard'
    _description = 'Warranty Extension Wizard'

    extension_period = fields.Integer(
        string="Extension Period",
        required=True,
        default=1,
    )
    extension_unit = fields.Selection(
        selection=[
            ('day', 'Days'),
            ('month', 'Months'),
            ('year', 'Years'),
        ],
        string="Extension Unit",
        required=True,
        default='month',
    )

    def _extension_to_days(self):
        """Convert the wizard's (extension_period, extension_unit) to days.

        Uses standard calendar averages so that successive extensions with
        different units accumulate correctly on a single integer field:
          • 1 day   = 1 day
          • 1 month = 30 days
          • 1 year  = 365 days
        """
        self.ensure_one()
        unit_map = {'day': 1, 'month': 30, 'year': 365}
        return self.extension_period * unit_map.get(self.extension_unit, 30)

    def action_confirm(self):
        """Stub — overridden by cyllo_warranty_sale and cyllo_warranty_purchase."""
        return {'type': 'ir.actions.act_window_close'}

