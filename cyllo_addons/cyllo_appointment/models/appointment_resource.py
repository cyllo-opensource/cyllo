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
from odoo import api, fields, models, _


class AppointmentResource(models.Model):
    _name = 'appointment.resource'
    _description = 'Appointment Resource'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='Resource Name', required=True, tracking=True)
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company
    )
    active = fields.Boolean(string='Active', default=True)
    color = fields.Integer(string='Color Index', default=0)
    resource_type = fields.Selection([
        ('room', 'Room / Space'),
        ('equipment', 'Equipment'),
        ('vehicle', 'Vehicle'),
        ('tool', 'Tool'),
        ('other', 'Other'),
    ], string='Type', default='room', required=True)
    description = fields.Text(string='Description')
    capacity = fields.Integer(string='Capacity', default=1,
                              help='Maximum number of people or units this resource can handle')
    location = fields.Char(string='Location')
    image = fields.Image(string='Image', max_width=256, max_height=256)
    # Availability
    working_hours_id = fields.Many2one(
        'resource.calendar', string='Working Hours',
        help='Override availability schedule for this specific resource'
    )
    # Linked appointment types
    appointment_type_ids = fields.Many2many(
        'appointment.type', 'appointment_type_resource_rel',
        'resource_id', 'type_id',
        string='Appointment Types'
    )
    # Stats
    appointment_count = fields.Integer(
        string='Appointments', compute='_compute_appointment_count'
    )

    @api.depends('name')
    def _compute_appointment_count(self):
        for rec in self:
            rec.appointment_count = self.env[
                'appointment.appointment'].search_count([
                ('resource_id', '=', rec.id)
            ])

    def action_view_appointments(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Appointments - %s') % self.name,
            'res_model': 'appointment.appointment',
            'view_mode': 'list,form,calendar',
            'domain': [('resource_id', '=', self.id)],
            'context': {'default_resource_id': self.id},
        }
