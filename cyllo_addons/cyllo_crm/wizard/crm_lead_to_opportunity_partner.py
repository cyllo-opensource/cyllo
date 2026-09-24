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
from odoo import models


class crmLeadToOpportunity(models.TransientModel):
    _inherit = 'crm.lead2opportunity.partner'

    def action_next_step(self):
        """next button to navigate to the wizard from where the user can compare fields of
        the duplicate leads carrying duplicate lead data as context"""
        duplicate_leads = self.duplicated_lead_ids  # Fetch duplicate leads from context
        return {
            'type': 'ir.actions.act_window',
            'name': 'Merge details',
            'res_model': 'crm.compare.fields',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_duplicate_lead': duplicate_leads.ids,
                        'default_parent': self.lead_id.id},
        }
