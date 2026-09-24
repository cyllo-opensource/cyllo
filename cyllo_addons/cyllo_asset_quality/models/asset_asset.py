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
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

class AssetAsset(models.Model):
    _inherit = 'asset.asset'

    quality_control_point_ids = fields.Many2many(
        'quality.control.point',
        'asset_quality_rel',
        'asset_id',
        'quality_id',
        string='Quality Control Points'
    )

    @api.onchange('asset_item_id')
    def _onchange_asset_item_id_quality(self):
        """Automatically assigns quality control points from the selected asset item when quality management is enabled."""
        if self.asset_item_id and self.asset_item_id.is_quality:
            self.quality_control_point_ids = self.asset_item_id.quality_control_point_id

    @api.constrains('quality_control_point_ids', 'is_lease_asset', 'is_rental_asset')
    def _check_quality_control_point_operation_type(self):
        """Validate that the selected quality control points match the asset operation type configuration."""
        for record in self:
            for quality_point in record.quality_control_point_ids:
                asset_operation_type = quality_point.asset_operation_type
                if asset_operation_type == 'lease' and not record.is_lease_asset:
                    raise ValidationError(_(
                        "The selected Quality Control Point is configured "
                        "for Lease operations, but '%s' is not a lease asset."
                    ) % quality_point.display_name)
                elif asset_operation_type == 'rent' and not record.is_rental_asset:
                    raise ValidationError(_(
                        "The selected Quality Control Point is configured "
                        "for Rental operations, but '%s' is not a rental asset."
                    ) % quality_point.display_name)
                elif asset_operation_type == 'both' and not (record.is_lease_asset or record.is_rental_asset):
                    raise ValidationError(_(
                        "The selected Quality Control Point requires an "
                        "asset configured for both Rental and Lease."
                    ))
