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


class ResConfigSettings(models.TransientModel):
    """class involves adding fields to crm settings"""
    _inherit = 'res.config.settings'
    deal_reminder = fields.Boolean(string="Deal Reminder",
                                   config_parameter='Cyllo_Crm.'
                                                    'deal_reminder')
    deal_reminder_days = fields.Selection([
        ('1', '1'),
        ('2', '2'),
        ('3', '3'),
        ('4', '4'),
        ('5', '5'),
        ('6', '6'),
        ('7', '7'),
        ('8', '8'),
        ('9', '9'),
        ('10', '10'),
    ], string='reminder', default='10',
        config_parameter='Cyllo_Crm.deal_reminder_days')

    is_exit_criteria_configured = fields.Boolean()

    stage_activity_ids = fields.Many2many('crm.stage.activity')

    module_cyllo_crm_advance_lead = fields.Boolean(string="Advance Lead")

    module_cyllo_crm_project = fields.Boolean(string="Cyllo CRM Project",
                                              help="Allows creating a project from a won CRM lead.",
                                              config_parameter='Cyllo_Crm.module_cyllo_crm_project')
    module_cyllo_visiting_card_digitization = fields.Boolean(
        string="Cyllo Visiting Card Digitization",
        help="Enable digitization of visiting cards to automatically extract contact details and create CRM leads.",
        config_parameter="cyllo_crm.module_cyllo_visiting_card_digitization"
    )
    module_cyllo_crm_survey = fields.Boolean(
        string="CRM Survey",
        help="Enable CRM Survey to create, manage, and analyze customer surveys directly within the CRM.",
        config_parameter="cyllo_crm.module_cyllo_crm_survey"
    )

    module_cyllo_crm_google_form = fields.Boolean(
        string="CRM Google Forms Integration",
        help="Enable CRM Google Forms to create, manage, and link Google Forms directly from CRM leads.",
        config_parameter="cyllo_crm.module_crm_google_form"
    )

    module_cyllo_google_meet = fields.Boolean(
        string="CRM Google Meet Integration",
        help="Enable CRM Google Meet to create, manage, and link Google Meet directly from CRM leads.",
        config_parameter="cyllo_crm.module_cyllo_google_meet"
    )

    module_cyllo_zoom = fields.Boolean(
        string="CRM Zoom Meet Integration",
        help="Enable CRM Zoom Meet to create, manage, and link Zoom meetings directly from CRM leads.",
        config_parameter="cyllo_crm.module_cyllo_zoom"
    )

    @api.onchange('module_cyllo_crm_advance_lead')
    def _onchange_module_cyllo_crm_advance_lead(self):
        if self.module_cyllo_crm_advance_lead:
            self.group_use_lead = True

    def set_values(self):
        """Override set_values to handle module installation properly"""
        super().set_values()

        Module = self.env['ir.module.module'].sudo()

        # Install Cyllo CRM Project module
        if self.module_cyllo_crm_project:
            crm_project_module = Module.search(
                [('name', '=', 'cyllo_crm_project'),
                 ('state', '!=', 'installed')],
                limit=1
            )
            if crm_project_module:
                crm_project_module.button_immediate_install()

        # Install Cyllo Visiting Card Digitization module
        if self.module_cyllo_visiting_card_digitization:
            visiting_card_module = Module.search(
                [('name', '=', 'cyllo_visiting_card_digitization'),
                 ('state', '!=', 'installed')],
                limit=1
            )
            if visiting_card_module:
                visiting_card_module.button_immediate_install()

        # Install CRM Survey module
        if self.module_cyllo_crm_survey:
            crm_survey_module = Module.search(
                [('name', '=', 'crm_survey'),
                 ('state', '!=', 'installed')],
                limit=1
            )
            if crm_survey_module:
                crm_survey_module.button_immediate_install()

        # Install CRM Google Forms module
        if self.module_cyllo_crm_google_form:
            crm_google_form_module = Module.search(
                [('name', '=', 'cyllo_crm_google_form'),
                 ('state', '!=', 'installed')],
                limit=1
            )
            if crm_google_form_module:
                crm_google_form_module.button_immediate_install()

        # Install CRM Google Meet module
        if self.module_cyllo_google_meet:
            crm_google_meet_module = Module.search(
                [('name', '=', 'cyllo_google_meet'),
                 ('state', '!=', 'installed')],
                limit=1
            )
            if crm_google_meet_module:
                crm_google_meet_module.button_immediate_install()

        # Install CRM Zoom Meet module
        if self.module_cyllo_zoom:
            crm_module_cyllo_zoom = Module.search(
                [('name', '=', 'cyllo_zoom'),
                 ('state', '!=', 'installed')],
                limit=1
            )
            if crm_module_cyllo_zoom:
                crm_module_cyllo_zoom.button_immediate_install()



    def action_configure_exit_criteria(self):
        """trigger a popup in crm settings and load previously created exit criterias"""
        self.ensure_one()

        # Get all CRM stages
        stages = self.env['crm.stage'].search([])

        # Create wizard record
        wizard = self.env['crm.stage.exit.criteria'].create({
            'stage_ids': [(6, 0, stages.ids)],
        })

        # Fetch existing exit criteria and add them to the wizard
        existing_criteria = self.env['crm.stage.activity'].search(
            [('is_exit_criteria', "=", True)])
        if existing_criteria:
            criteria_vals = []
            for criteria in existing_criteria:
                criteria_vals.append((0, 0, {
                    'stage_id': criteria.stage_id.id,
                    'activity_id': criteria.activity_id.id,
                    'user_id': criteria.user_id.id if hasattr(criteria,
                                                              'user_id') else False,
                }))
            wizard.write({'exit_criteria_ids': criteria_vals})

        # Check if no data was added to the wizard
        has_criteria = bool(wizard.exit_criteria_ids)

        return {
            'name': 'Configure Stage Exit Criteria',
            'type': 'ir.actions.act_window',
            'res_model': 'crm.stage.exit.criteria',
            'view_mode': 'form',
            'res_id': wizard.id,
            'target': 'new',
            'context': {'has_criteria': has_criteria}  # Pass this to the view
        }
