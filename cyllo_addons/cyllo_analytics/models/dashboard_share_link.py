# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cyllo(<https://www.cyllo.com>)
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
from odoo import models, fields, api
import uuid
from datetime import timedelta

class DashboardShareLink(models.Model):
    _name = 'dashboard.share.link'
    _description = 'Dashboard Share Link'

    dashboard_id = fields.Many2one('dashboard.config', string="Dashboard", required=True, ondelete='cascade')
    access_token = fields.Char("Access Token", default=lambda self: str(uuid.uuid4()), required=True, copy=False)
    expiry_date = fields.Datetime("Expiration Date")
    is_active = fields.Boolean("Active", default=True)
    access_url = fields.Char("Access URL", compute="_compute_access_url", store=True, precompute=True)
    date_from = fields.Date("Date From")
    date_to = fields.Date("Date To")
    sheet_queries = fields.Text("Sheet Queries")

    @api.depends('access_token')
    def _compute_access_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for rec in self:
            rec.access_url = f"{base_url}/dashboard/share/{rec.access_token}"

    def revoke(self):
        self.write({'is_active': False})

    @api.model
    def purge_expired_links(self):
        """Cron job to deactivate expired links."""
        expired = self.search([('is_active', '=', True), ('expiry_date', '<', fields.Datetime.now())])
        expired.write({'is_active': False})
