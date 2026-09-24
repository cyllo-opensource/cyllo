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


class CrmStageExitCriteriaLine(models.TransientModel):
    """wizard to add exit criteria lines in the popup in CRM settings"""
    _name = 'crm.stage.exit.criteria.line'
    _description = 'CRM Stage Exit Criteria Line'

    wizard_id = fields.Many2one('crm.stage.exit.criteria', string='Wizard')
    stage_id = fields.Many2one(
        'crm.stage',
        string='Stage',
        required=True, domain='[("is_won","=",False)]'
    )
    company_id = fields.Many2one('res.company', string='Company', index=True,
                                 default=lambda self: self.env.company)
    activity_id = fields.Many2one(
        'mail.activity.type',
        string='Required Activity',
        required=True
    )
    user_id = fields.Many2one('res.users', string="Assigned user")

    @api.onchange('wizard_id')
    def _onchange_wizard_id(self):
        """Update domain for stage_id when wizard changes"""
        if self.wizard_id:
            # Get stages already used in other lines
            used_stages = self.env['crm.stage.exit.criteria.line'].search([
                ('wizard_id', '=', self.wizard_id.id),
                ('id', '!=', self._origin.id or 0)  # Exclude current record
            ]).mapped('stage_id.id')

            return {'domain': {'stage_id': [('id', 'not in', used_stages)]}}

    @api.model
    def create(self, vals):
        """Override create to validate no duplicate stages"""
        record = super(CrmStageExitCriteriaLine, self).create(vals)
        # Check for duplicates after creation
        self._check_duplicate_stages(record)
        return record

    def write(self, vals):
        """Override write to validate no duplicate stages"""
        result = super(CrmStageExitCriteriaLine, self).write(vals)
        # Check for duplicates after update
        for record in self:
            self._check_duplicate_stages(record)
        return result

    @api.model
    def _check_duplicate_stages(self, record):
        """Check and prevent duplicate stages"""
        if record.stage_id and record.wizard_id:
            duplicate = self.search([
                ('wizard_id', '=', record.wizard_id.id),
                ('stage_id', '=', record.stage_id.id),
                ('id', '!=', record.id)
            ], limit=1)

            if duplicate:
                raise ValidationError(
                    _("Stage '%s' is already used in another exit criteria line.") % record.stage_id.name)
