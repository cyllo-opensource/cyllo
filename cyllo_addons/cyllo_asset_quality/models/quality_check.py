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


class QualityCheck(models.Model):
    _inherit = 'quality.check'

    control_type = fields.Selection(selection_add=[('asset', 'Asset')], ondelete={'asset': 'cascade'})
    asset_operation_type = fields.Selection([
        ('lease', 'Lease'),
        ('rent', 'Rent')
    ], string="Operation Type", tracking=True)
    asset_ids = fields.Many2many('asset.asset', string="Assets", tracking=True)
    asset_rental_id = fields.Many2one('asset.rental', string="Rental", tracking=True)
    asset_lease_id = fields.Many2one('asset.lease', string="Lease", tracking=True)
