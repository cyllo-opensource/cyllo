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
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class FrontdeskFrontdesk(models.Model):
    _name = 'frontdesk.frontdesk'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Frontdesk Station'
    _order = 'name'

    name = fields.Char(string='Station Name', required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    responsible_ids = fields.Many2many('hr.employee', string='Responsible Employees', help='Employees responsible for this station who will receive notifications')
    is_host = fields.Boolean(string='Host Selection', default=True, help='Allows the visitor to pick the host of the meeting from the list')
    is_drink = fields.Boolean(string='Offer Drinks', default=True, help='Allow visitor to select a drink during registration')
    notify_by_email = fields.Boolean(string='Notify by Email', default=True)
    notify_by_sms = fields.Boolean(string='Notify by SMS', default=False)
    notify_by_discuss = fields.Boolean(string='Notify by Discuss', default=False)
    drink_selection_ids = fields.Many2many('frontdesk.drink', string='Drinks Offered')
    visitor_ids = fields.One2many('frontdesk.visitor', 'station_id', string='Visitors')
    visitor_count = fields.Integer(string='Visitor Count', compute='_compute_visitor_count')
    has_emergency_alert = fields.Boolean(
        string='Has Emergency Alert',
        compute='_compute_has_emergency_alert',
    )
    
    @api.depends('visitor_ids')
    def _compute_visitor_count(self):
        for station in self:
            station.visitor_count = len(station.visitor_ids.filtered(lambda v: v.state in ('planned', 'checked_in')))

    def _compute_has_emergency_alert(self):
        alert_model = self.env['frontdesk.emergency.alert']
        for station in self:
            station.has_emergency_alert = bool(station.id and alert_model.search_count([
                ('active', '=', True),
                ('station_ids', 'in', station.id),
            ]))

    def action_open_visitors(self):
        self.ensure_one()
        return {
            'name': f'Visitors at {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'frontdesk.visitor',
            'view_mode': 'tree,form,calendar',
            'domain': [('station_id', '=', self.id)],
            'context': {'default_station_id': self.id},
        }

    def action_quick_register_visitor(self):
        self.ensure_one()
        return {
            'name': 'Register Visitor',
            'type': 'ir.actions.act_window',
            'res_model': 'frontdesk.visitor',
            'view_mode': 'form',
            'target': 'current',
            'context': {'default_station_id': self.id},
        }

    def action_configure_drinks(self):
        return {
            'name': 'Configure Drinks',
            'type': 'ir.actions.act_window',
            'res_model': 'frontdesk.drink',
            'view_mode': 'tree,form',
            'target': 'current',
        }

    def action_trigger_emergency(self):
        self.ensure_one()
        if not self.has_emergency_alert:
            raise UserError(_("No emergency alert is configured for this station."))
        return {
            'name': 'Trigger Emergency Alert',
            'type': 'ir.actions.act_window',
            'res_model': 'frontdesk.emergency.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_station_id': self.id,
            }
        }
