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
from odoo import api, models, fields
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, date, time
import logging

_logger = logging.getLogger(__name__)

class IrModel(models.Model):
    """Extension of ir.model.fields for Studio-created fields."""
    _inherit = 'ir.model.fields'

    is_studio = fields.Boolean(string='Studio Field', default=False,
                               help="Notify field created through Studio")

    constraint_code = fields.Text(
        string='Constraint Code',
        help='Python code for field validation'
    )
    constraint_fields = fields.Char(
        string='Constraint Dependencies',
        help='Comma-separated field names that trigger this constraint'
    )
    # constraint_message = fields.Char(string='Constraint Message')

    @api.model
    def create_new_fields(self, args):
        """Create a new custom field for a model."""
        model = self.env['ir.model'].search([('model', '=', args['model'])])
        technical_name = 'x_cy_' + args['technical_name']
        ir_model_field = self.create({
            'name': technical_name,
            'complete_name': args['label'],
            'model': args['model'],
            'model_id': model.id,
            'ttype': args['field_type'],
            'field_description': args['help'],
            'state': 'manual',
            'is_studio': True
        })

    @api.model
    def _load_all_constraints(self):
        """Load all studio constraints into their models"""
        try:
            # Use sudo() to ensure we can read all constraint fields
            constraint_fields = self.sudo().search([
                ('constraint_code', '!=', False),
                ('constraint_fields', '!=', False),
               ('state', '=', 'manual'),
            ])

            _logger.info(f"Loading {len(constraint_fields)} studio constraints")

            for field_rec in constraint_fields:
                try:
                    self._inject_constraint(field_rec)
                except Exception as e:
                    _logger.error(f"Failed to inject constraint for {field_rec.name}: {e}")

        except Exception as e:
            _logger.error(f"Failed to load studio constraints: {e}", exc_info=True)

    def _inject_constraint(self, field_rec):
        """Inject a single constraint into a model"""
        try:
            # Verify model exists
            if field_rec.model not in self.env.registry:
                _logger.warning(f"Model {field_rec.model} not found")
                return

            Model = self.env.registry[field_rec.model]

            # Parse dependencies
            deps = [
                f.strip()
                for f in (field_rec.constraint_fields or '').split(',')
                if f.strip()
            ]

            if not deps:
                _logger.warning(f"No constraint dependencies for {field_rec.name}")
                return

            # Verify dependencies exist
            for dep in deps:
                if dep not in Model._fields:
                    _logger.warning(
                        f"Field {dep} not found in {field_rec.model} "
                        f"(constraint on {field_rec.name})"
                    )
                    return

            # Store the code in a variable to avoid closure issues
            code = field_rec.constraint_code
            field_name = field_rec.name

            # Create constraint function
            def _studio_constraint(records):
                """Dynamically created studio constraint"""
                safe_globals = {
                    'ValidationError': ValidationError,
                    'UserError': UserError,
                    'datetime': datetime,
                    'date': date,
                    'time': time,
                    '_logger': _logger,
                }

                local_vars = {
                    'self': records,
                    'env': records.env,
                }

                try:
                    # Execute the constraint code
                    exec(code, safe_globals, local_vars)

                except ValidationError:
                    raise
                except Exception as e:
                    _logger.error(
                        f"Error in studio constraint {field_name}: {e}",
                        exc_info=True
                    )
                    raise ValidationError(f"Constraint error: {str(e)}")

            # Set constraint metadata
            _studio_constraint._constrains = deps

            # Generate unique method name
            method_name = f'_check_studio_{field_rec.id}'

            # Remove old constraint if exists
            if hasattr(Model, method_name):
                delattr(Model, method_name)

            # Add new constraint
            setattr(Model, method_name, _studio_constraint)

            # Clear constraint cache
            if hasattr(Model, '_constraint_methods'):
                try:
                    delattr(Model, '_constraint_methods')
                except AttributeError:
                    pass

            _logger.info(
                f"Injected constraint {method_name} on {field_rec.model} "
                f"watching {deps}"
            )

        except Exception as e:
            _logger.error(
                f"Failed to inject constraint for {field_rec.name}: {e}",
                exc_info=True
            )

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to inject constraints for new fields"""
        records = super(IrModel, self).create(vals_list)

        for record in records:
            if record.constraint_code and record.constraint_fields:
                try:
                    self._inject_constraint(record)
                except Exception as e:
                    _logger.error(f"Failed to inject constraint on create: {e}")

        return records

    def write(self, vals):
        """Override write to update constraints"""
        res = super(IrModel, self).write(vals)

        # Re-inject if constraint code/fields changed
        if 'constraint_code' in vals or 'constraint_fields' in vals:
            for record in self:
                if record.constraint_code and record.constraint_fields:
                    try:
                        self._inject_constraint(record)
                    except Exception as e:
                        _logger.error(f"Failed to update constraint: {e}")

        return res

class IrUiView(models.Model):
    """Extension of ir.ui.view for Studio-created views."""
    _inherit = 'ir.ui.view'

    is_studio = fields.Boolean(string='Studio Field', default=False,
                               help="Notify field created through Studio")
