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
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class TemplateVariable(models.Model):
    """Model representing Template Variables."""
    _name = 'template.variable'
    _description = 'Template Header and Body Variable'

    template_id = fields.Many2one('whatsapp.template',
                                  help='The template name of template variables')
    type = fields.Selection([('header', 'Header'), ('body', 'Body')],
                            help='The type of template variable')
    display_name = fields.Char(
        help="""*The display name of variable. * Must be a unique name and can only contain lowercase alphanumeric characters.""")
    sample_value = fields.Char(required=True,
                               help='The sample value of variable')
    variable_value = fields.Char(string='Field Name',
                                 help='Enter the field name of selected model',
                                 required=True)
    model_id = fields.Many2one('ir.model', related='template_id.model_id',
                               help='The reference model for template')

    @api.constrains('variable_value')
    def _check_variable_value(self):
        """Check the validity of the variable_value field.
            Raises:
                ValidationError: If the 'variable_value' field contains an
                invalid field path, or if the user does not have read access to
                the referenced model.
            Returns:
                None """
        for record in self:
            model = self.env[self.model_id.model]
            if not model.check_access_rights('read', raise_exception=False):
                raise ValidationError(
                    _("You are not allowed access the fields in %r."
                      "\n Contact your administrator to request access if necessary.",
                      model))
            variables = record.variable_value.split('.')
            current_model = model
            for var in variables:
                if var not in current_model._fields:
                    raise ValidationError(
                        _("Invalid field name '%s' in model '%s'.", var,
                          current_model._name)
                    )

                field = current_model._fields[var]
                if field.type == 'many2one':
                    current_model = field.comodel_name and current_model.env[
                        field.comodel_name]
                else:
                    if var != variables[-1]:
                        raise ValidationError(
                            _("Field '%s' in model '%s' is not a relational field. Invalid path segment after it.",
                              var,
                              current_model._name)
                        )
