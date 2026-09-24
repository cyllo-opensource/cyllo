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


class QualityControlPoint(models.Model):
    _inherit = 'quality.control.point'

    qc_check_for = fields.Selection(selection_add=[('asset', 'Asset')], ondelete={'asset': 'cascade'})
    asset_ids = fields.Many2many(
        'asset.asset',
        'asset_quality_rel',
        'quality_id',
        'asset_id',
        string='Assets'
    )
    asset_operation_type = fields.Selection([
        ('lease', 'Lease'),
        ('rent', 'Rent'),
        ('both', 'Both')
    ], string="Asset Operation Type")
    operation_type_ids = fields.Many2many(required=False)
