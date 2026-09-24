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
from odoo.exceptions import UserError


class AssetRental(models.Model):
    _inherit = 'asset.rental'

    quality_check_ids = fields.One2many(
        'quality.check',
        'asset_rental_id',
        compute='_compute_quality_check_ids',
        string="Quality Checks"
    )
    is_quality_point = fields.Boolean(
        compute='_compute_has_quality_point',
        store=True
    )
    show_validate_quality = fields.Boolean(
        compute='_compute_quality_buttons'
    )
    show_revalidate_quality = fields.Boolean(
        compute='_compute_quality_buttons'
    )

    @api.depends('quality_check_ids.state', 'quality_check_ids.quality_control_id')
    def _compute_quality_buttons(self):
        """Compute the visibility of quality action buttons."""
        for record in self:
            record.show_validate_quality = False
            record.show_revalidate_quality = False
            if not record.quality_check_ids:
                record.show_validate_quality = True
                continue
            grouped = {}
            for quality_check in record.quality_check_ids:
                control_point_id = quality_check.quality_control_id.id
                if control_point_id not in grouped:
                    grouped[control_point_id] = []
                grouped[control_point_id].append(quality_check.state)
            pending_exists = False
            failed_exists = False
            for states in grouped.values():
                if any(state not in ['pass', 'fail'] for state in states):
                    pending_exists = True
                elif 'fail' in states and 'pass' not in states:
                    failed_exists = True
            if pending_exists:
                record.show_validate_quality = True
            elif failed_exists:
                record.show_revalidate_quality = True

    def _compute_quality_check_ids(self):
        """Compute and retrieve quality checks linked to the current rental record."""
        for record in self:
            record.quality_check_ids = self.env['quality.check'].search([
                ('asset_rental_id', '=', record.id)
            ])

    @api.depends("asset_id")
    def _compute_has_quality_point(self):
        """Compute whether the selected asset contains configured quality control points."""
        for record in self:
            values = record.asset_id.quality_control_point_ids.mapped('asset_operation_type')
            record.is_quality_point = 'both' in values or 'rent' in values

    def action_return_asset(self):
        """Process asset return and create maintenance requests for failed quality inspections."""
        res = super().action_return_asset()
        for record in self:
            quality_checks_list = self.env['quality.check'].search([
                ('asset_rental_id', '=', record.id),
                ('asset_ids', 'in', record.asset_id.ids),
            ])
            for quality_check in quality_checks_list:
                failed_lines = quality_check.quality_check_line_ids.filtered(lambda line: line.status == 'fail')
                if not failed_lines:
                    continue
                self.env['maintenance.request'].create({
                    'name': f"Repair Request for {record.asset_id.name} (Rental Return)",
                    'asset_id': record.asset_id.id,
                    'maintenance_type': 'corrective',
                    'user_id': self.env.user.id,
                    'description': "\n".join(
                        [f"Quality Check Failed: {quality_check.name}"] +
                        [f"- {line.inspection_type_id.name}" for line in failed_lines]
                    ),
                })
                record.asset_id.is_repair = True
        return res

    def action_revalidate_quality(self):
        """Create new quality recheck records for failed quality validations."""
        self.ensure_one()
        grouped_checks = {}
        for quality_check in self.quality_check_ids:
            control_point_id = quality_check.quality_control_id.id
            if control_point_id not in grouped_checks:
                grouped_checks[control_point_id] = self.env['quality.check']
            grouped_checks[control_point_id] |= quality_check
        for control_point_id, quality_checks in grouped_checks.items():
            states = quality_checks.mapped('state')
            if 'pass' in states:
                continue
            if any(state not in ['pass', 'fail'] for state in states):
                continue
            if 'fail' in states:
                self.env['quality.check'].create({
                    'name': f"Recheck - {self.asset_id.display_name}",
                    'quality_control_id': control_point_id,
                    'control_type': 'asset',
                    'asset_operation_type': 'rent',
                    'asset_ids': [(6, 0, [self.asset_id.id])],
                    'asset_rental_id': self.id,
                    'user_id': self.env.user.id,
                })

    def action_validate_quality(self):
        """Validate quality checks for the current rental asset."""
        self.ensure_one()
        if self.status != 'rent':
            raise UserError(
                _("You can only validate quality for active rentals.")
            )
        if not self.asset_id:
            raise UserError(
                _("Please select an asset before validating quality.")
            )
        control_points = self.asset_id.quality_control_point_ids.filtered(
            lambda point: point.asset_operation_type in ['rent', 'both']
        )
        if not control_points:
            raise UserError(
                _("No Quality Control Point defined for asset: %s")
                % self.asset_id.display_name
            )
        existing_quality_checks = self.env['quality.check'].search([
            ('asset_rental_id', '=', self.id),
            ('asset_ids', 'in', self.asset_id.ids),
        ])
        grouped_checks = {}
        for quality_check in existing_quality_checks:
            control_point_id = quality_check.quality_control_id.id
            if control_point_id not in grouped_checks:
                grouped_checks[control_point_id] = self.env['quality.check']
            grouped_checks[control_point_id] |= quality_check
        for control_point in control_points:
            quality_checks = grouped_checks.get(
                control_point.id,
                self.env['quality.check']
            )
            states = quality_checks.mapped('state')
            if not quality_checks:
                self.env['quality.check'].create({
                    'name': f"Rental Check - {self.asset_id.display_name}",
                    'quality_control_id': control_point.id,
                    'control_type': 'asset',
                    'asset_operation_type': 'rent',
                    'asset_ids': [(6, 0, [self.asset_id.id])],
                    'asset_rental_id': self.id,
                    'user_id': self.env.user.id,
                })
                continue
            if 'pass' in states:
                continue
            if any(state not in ['pass', 'fail'] for state in states):
                continue
            if 'fail' in states:
                self.env['quality.check'].create({
                    'name': f"Recheck - {self.asset_id.display_name}",
                    'quality_control_id': control_point.id,
                    'control_type': 'asset',
                    'asset_operation_type': 'rent',
                    'asset_ids': [(6, 0, [self.asset_id.id])],
                    'asset_rental_id': self.id,
                    'user_id': self.env.user.id,
                })
        return {
            'name': _('Quality Check'),
            'type': 'ir.actions.act_window',
            'res_model': 'quality.check',
            'view_mode': 'tree,form',
            'target': 'current',
            'domain': [('asset_rental_id', '=', self.id)],
        }

    def view_quality_checks(self):
        """Open all quality checks associated with the current rental record."""
        return {
            'name' : 'Quality Checks',
            'type' : 'ir.actions.act_window',
            'res_model': 'quality.check',
            'view_mode': 'tree,form',
            'target': 'current',
            'domain' : [('asset_rental_id', '=', self.id)],
        }
