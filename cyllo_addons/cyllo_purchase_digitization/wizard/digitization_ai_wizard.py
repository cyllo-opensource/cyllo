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
from odoo import  models

class DigitizationAiWizard(models.TransientModel):
    """This model is used to switch the active configuration into ai configuration """
    _name = 'digitization.ai.wizard'
    _description = 'Switch to AI Digitization'

    def action_switch_to_ai(self):
        """this method is used to convert manual digitize to ai digitize if manual digitize fails"""
        active_id = self.env.context.get('active_id')
        record = self.env['purchase.order'].browse(active_id)
        purchase_digitization = self.env[
            'purchase.digitization'].search(
            [('active_configuration', '=', True)])
        purchase_digitization.write({'automation_method':'ai_digitization'})
        record.action_send_digitization()

