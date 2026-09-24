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
from datetime import datetime

from odoo import api, fields, models


class Lead(models.Model):
    """Inherit crm.lead to add a field"""
    _inherit = "crm.lead"

    is_closed_on_time = fields.Boolean(string="Closed Within Deadline",
                                       compute="_compute_is_closed_on_time",
                                       store=True)
    is_new_customer = fields.Boolean(string="Is New Customer",
                                     compute="_compute_is_new_customer",
                                     store=True)

    @api.depends('stage_id', 'date_closed', 'date_deadline')
    def _compute_is_closed_on_time(self):
        """Compute if the lead is closed on time based on the deadline."""
        for rec in self:
            rec.is_closed_on_time = False
            if rec.stage_id.is_won and rec.date_deadline and rec.date_closed:
                deadline_dt = datetime.combine(rec.date_deadline,
                                               datetime.max.time())
                rec.is_closed_on_time = True if rec.date_closed <= deadline_dt else False

    @api.depends('partner_id')
    def _compute_is_new_customer(self):
        """Compute if the lead is a new customer based on no previous leads."""
        for rec in self:
            rec.is_new_customer = False
            if rec.partner_id:
                previous_leads = self.env['crm.lead'].search([
                    ('partner_id', '=', rec.partner_id.id),
                    ('id', '!=', rec.id),
                    ('create_date', '<', rec.create_date),
                ])
                rec.is_new_customer = True if not previous_leads else False
