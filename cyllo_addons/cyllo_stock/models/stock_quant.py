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

import datetime
from odoo import api, fields, models, _
from odoo.osv import expression


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    expiry_risk_level = fields.Selection([
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
        ('no_expiry', 'No expiry')
    ], string="Risk Details", compute="_compute_expiry_risk_level",
        search="_search_expiry_risk_level")

    is_handled = fields.Boolean(string="Is Handled", default=False, copy=False)

    def _search_expiry_risk_level(self, operator, value):
        if operator not in ('=', 'in') or 'expiration_date' not in self.env['stock.lot']._fields:
            return []

        today = fields.Datetime.now()
        thirty_days_later = today + datetime.timedelta(days=30)

        target_values = [value] if isinstance(value, str) else value

        lot_domains = []
        for val in target_values:
            if val == 'high':
                lot_domains.append([('alert_date', '<=', today)])
            elif val == 'medium':
                lot_domains.append([
                    ('expiration_date', '<=', thirty_days_later),
                    '|', ('alert_date', '>', today), ('alert_date', '=', False)
                ])
            elif val == 'low':
                lot_domains.append([
                    ('expiration_date', '>', thirty_days_later),
                    '|', ('alert_date', '>', today), ('alert_date', '=', False)
                ])

        combined_domain = expression.OR(lot_domains) if lot_domains else []
        final_lot_domain = expression.AND(
            [[('expiration_date', '!=', False)], combined_domain]) if combined_domain else [
            ('id', '=', 0)]

        lots = self.env['stock.lot'].search(final_lot_domain)
        return [('lot_id', 'in', lots.ids), ('quantity', '!=', 0.0)]

    @api.depends('quantity')
    def _compute_expiry_risk_level(self):
        today = fields.Datetime.now()
        for quant in self:
            if 'expiration_date' not in self.env[
                'stock.lot']._fields or not quant.lot_id or not quant.lot_id.expiration_date or quant.quantity <= 0.0:
                quant.expiry_risk_level = 'no_expiry'
                continue

            alert_date = quant.lot_id.alert_date
            expiration_date = quant.lot_id.expiration_date

            if alert_date and alert_date <= today:
                quant.expiry_risk_level = 'high'
            elif expiration_date and expiration_date <= today + datetime.timedelta(days=30):
                quant.expiry_risk_level = 'medium'
            else:
                quant.expiry_risk_level = 'low'

    def action_handle_expiry(self):
        self.ensure_one()
        return {
            'name': _('Handle Expiry: %s') % self.product_id.display_name,
            'type': 'ir.actions.act_window',
            'res_model': 'stock.quant.handle.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_quant_id': self.id,
            }
        }

    @api.model
    def action_view_inventory(self):
        action = super().action_view_inventory()
        if action.get('domain'):
            action['domain'] = expression.AND([action['domain'], [('quantity', '!=', 0.0)]])
        else:
            action['domain'] = [('quantity', '!=', 0.0)]
        return action
