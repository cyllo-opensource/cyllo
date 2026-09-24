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
import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)

class CompareRecord(models.TransientModel):
    """class to manage fields that goes through comparison while merging duplicate leads"""
    _name = 'crm.compare.record'
    _description = 'Duplicate Lead/Opportunity Record'

    lead_id = fields.Many2one('crm.lead', string="Lead ID")
    compare_id = fields.Many2one('crm.compare.fields', string="Compare")
    name = fields.Char(string="Name")
    email_from = fields.Char(string="Email")
    user_id = fields.Many2one('res.users', string="Assigned To")
    team_id = fields.Many2one('crm.team', string="Sales Team")
    stage_id = fields.Many2one('crm.stage', string="Stage")
    create_date = fields.Datetime(string="Creation Date")
    function = fields.Char(string="Job Position")
    phone = fields.Char(string="Phone")
    state = fields.Many2one('res.country.state')
    country = fields.Many2one('res.country')
    company_id = fields.Many2one('res.company', string='Company', index=True,
                                 default=lambda self: self.env.company)


class CompareFields(models.TransientModel):
    _name = 'crm.compare.fields'
    _description = 'Comparing fields on merging'

    duplicate_ids = fields.One2many('crm.compare.record', 'compare_id',
                                    string="Duplicate Leads")
    dissimilar_field_names = fields.One2many('dissimilar.fields', 'compare_id',
                                             string="Dissimilar Fields")

    @api.onchange('duplicate_ids')
    def _onchange_duplicate_ids(self):
        """method to manage duplicate ids, whenever duplicate leads/chosen leads changes through
         different provisions on merging"""
        self.ensure_one()
        self.dissimilar_field_names = [(5, 0, 0)]

        if not self.duplicate_ids:
            return

        # Define fields to exclude
        excluded_fields = {
            'id', 'compare_id', 'email_from', 'create_date',
            'write_date', 'lead_id', 'display_name', 'stage_id', 'street',
        }

        child_model = self.env['crm.compare.record']
        # Filter out excluded fields
        field_names = [f for f in child_model._fields.keys()
                       if f not in excluded_fields]

        field_metadata = child_model.fields_get(field_names)

        dissimilar_fields = []
        for field in field_names:
            values = []
            for dup in self.duplicate_ids:
                value = getattr(dup, field)
                if value:
                    if isinstance(value, models.BaseModel):
                        values.append(str(value.name))
                    else:
                        values.append(str(value))
            # Only consider fields with different non-empty values
            unique_values = list(set(v for v in values if v))
            if len(unique_values) > 1:
                dissimilar_fields.append((0, 0, {
                    'name': field_metadata[field]['string'],
                    'field_values': ', '.join(unique_values),
                }))

        if dissimilar_fields:
            self.write({
                'dissimilar_field_names': dissimilar_fields
            })

    def _convert_and_allocate(self, opportunity):
        """method to convert leads to opportunity"""
        if not opportunity.partner_id:
            partner = self.env['res.partner'].create({
                'name': opportunity.name,
                'email': opportunity.email_from,
            })
            opportunity.write({'partner_id': partner.id})

        opportunity.convert_opportunity(partner=opportunity.partner_id)

    def apply_merge(self):
        """
        Merge duplicate leads by updating the primary lead with selected values
        and deleting other duplicates.

        Returns:
            dict: Action to open the merged lead form view
        """
        # Get and validate leads to merge
        to_merge = self.env['crm.lead'].browse(
            self.env.context.get('default_duplicate_lead')).exists()

        if len(to_merge) < 2:
            return False

        # Perform initial merge
        result_opportunity = to_merge.merge_opportunity(auto_unlink=False)
        default_parent = self.env.context.get('default_parent')

        # Handle parent mismatch
        if result_opportunity.id != default_parent:
            if len(to_merge) == 2:
                result_opportunity = to_merge - result_opportunity
            else:
                to_merge -= result_opportunity
                result_opportunity = to_merge.merge_opportunity(
                    auto_unlink=False)

        # Ensure record is active
        result_opportunity.action_unarchive()

        # Process field values
        values_to_write = {}
        lead_fields_map = {
            field_obj.string.strip(): (fname, field_obj)
            for fname, field_obj in self.env['crm.lead']._fields.items()
        }

        for dissimilar_field in self.dissimilar_field_names:
            if not dissimilar_field.name:
                continue
            field_name = dissimilar_field.name.strip()
            field_values = [v.strip() for v in
                            (dissimilar_field.field_values or '').split(',') if
                            v.strip()]

            if not field_values:
                continue

            selected_value = field_values[0]

            # Get corresponding field object
            if field_name not in lead_fields_map:
                continue

            fname, field_obj = lead_fields_map[field_name]

            # Process field value based on field type
            if field_obj.type == 'many2one':
                related_model = self.env[field_obj.comodel_name]
                domain = [('name', '=', selected_value)]
                record = related_model.search(domain, limit=1)

                if record:
                    values_to_write[fname] = record.id
                else:
                    _logger.warning(
                        "No related record found for %s: %s",
                        field_name,
                        selected_value,
                    )
            else:
                values_to_write[fname] = selected_value

        # Write values and handle debugging
        if values_to_write:
            try:
                result_opportunity.write(values_to_write)
            except Exception as e:
                raise

        # Convert lead if necessary
        if result_opportunity.type == "lead":
            self._convert_and_allocate(result_opportunity)

        # Clean up other leads
        (to_merge - result_opportunity).unlink()

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'crm.lead',
            'view_mode': 'form',
            'res_id': result_opportunity.id,
            'target': 'current',
        }

    @api.model
    def default_get(self, fields):
        """Initialize the form with duplicate lead information."""
        res = super(CompareFields, self).default_get(fields)

        # Get duplicate leads from context
        duplicate_ids = self.env.context.get('default_duplicate_lead')

        if duplicate_ids:
            # Browse the leads
            duplicates = self.env['crm.lead'].browse(duplicate_ids)
            duplicate_data = []

            for dup in duplicates:
                vals = {
                    'lead_id': dup.id,
                    'name': dup.name,
                    'email_from': dup.email_from,
                    'phone': dup.phone,
                    'country': dup.country_id,
                    'state': dup.state_id,
                    'function': dup.function,
                    'create_date': dup.create_date,
                    'user_id': dup.user_id,
                    'team_id': dup.team_id,

                }

                # Handle related fields
                for field in ['user_id', 'team_id', 'stage_id']:
                    related_record = getattr(dup, field)
                    vals[field] = related_record.id if related_record else False

                duplicate_data.append((0, 0, vals))

            res['duplicate_ids'] = duplicate_data

        return res


class DissimilarFields(models.TransientModel):
    """class to manage dissimilar fields"""
    _name = 'dissimilar.fields'
    _description = 'Dissimilar Fields'

    name = fields.Char(string=" Dissimilar Fields")
    field_values = fields.Char(
        string="Field Values")  # Field values as a comma-separated string
    compare_id = fields.Many2one('crm.compare.fields', string="Parent Record")
