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
from odoo.exceptions import ValidationError


class ModelAccess(models.Model):
    _name = 'model.access'
    _description = 'Model Access'
    _rec_name = 'model_id'

    profile_management_id = fields.Many2one(
        'profile.management',
        string='Profile Management ID',
        help="The profile management record this rule belongs to."
    )
    model_id = fields.Many2one(
        'ir.model',
        string='Model',
        required=True,
        ondelete='cascade',
        help="The target Cyllo model for access control rules."
    )
    is_readonly = fields.Boolean(
        'Read-only',
        help="Make this model entirely read-only for the profile."
    )
    hide_create = fields.Boolean(
        'Hide Create',
        help="Hide the Create/New action button for this model."
    )
    hide_edit = fields.Boolean(
        'Hide Edit',
        help="Hide the Edit action button for this model."
    )
    hide_delete = fields.Boolean(
        'Hide Delete',
        help="Disable and hide record deletion capabilities for this model."
    )
    hide_archive = fields.Boolean(
        'Hide Archive/Unarchive',
        help="Hide Archive and Unarchive actions on records."
    )
    hide_duplicate = fields.Boolean(
        'Hide Duplicate',
        help="Hide the Duplicate action on records."
    )
    hide_export = fields.Boolean(
        'Hide Export',
        help="Disable and hide data export functionality for this model."
    )
    hide_reports = fields.Boolean(
        'Hide Reports',
        help="Hide reports / print menu options for this model."
    )
    hide_actions = fields.Boolean(
        'Hide Actions',
        help="Hide contextual actions / gear menu for this model."
    )

    @api.constrains(
        'is_readonly',
        'hide_create',
        'hide_edit',
        'hide_delete',
        'hide_archive',
        'hide_duplicate',
        'hide_export',
        'hide_reports',
        'hide_actions',
    )
    def _check_attribute(self):
        """Ensure that at least one access restriction is enabled."""
        for record in self:
            if not any([
                record.is_readonly,
                record.hide_create,
                record.hide_edit,
                record.hide_delete,
                record.hide_archive,
                record.hide_duplicate,
                record.hide_export,
                record.hide_reports,
                record.hide_actions,
            ]):
                raise ValidationError('Provide at least one attribute')
