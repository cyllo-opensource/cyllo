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
from odoo.exceptions import ValidationError


class SignGenerate(models.TransientModel):
    _name = 'sign.generate'
    _description = 'Sign Generate'

    name = fields.Char(string='File name', related='template_id.name')
    template_id = fields.Many2one('sign.template')
    validity = fields.Date()
    signer_ids = fields.One2many('sign.signers', 'sign_generate_id')
    contact_ids = fields.Many2many('res.partner', string='CC Recipients')
    subject = fields.Char()
    message = fields.Html()
    is_active = fields.Boolean("Active", compute="_compute_is_active",
                               help="Is active template", store=True, default=False)
    res_model = fields.Char(string='Source Model')
    res_id = fields.Integer(string='Source ID')

    @api.depends('template_id')
    def _compute_is_active(self):
        for rec in self:
            rec.is_active = False
            if rec.template_id and any(rec.template_id.item_ids.mapped('role_id')):
                rec.is_active = True

    @api.model
    def create(self, vals):
        res = super(SignGenerate, self).create(vals)
        if res.template_id and not res.signer_ids:
            sign_sign = self.env['sign.signers'].create([{
                'role_id': val.id,
                'sign_generate_id': res.id,
            } for val in res.template_id.item_ids.mapped('role_id') if val])
        return res

    def action_send(self):
        users = self.env['res.users'].sudo().search([('partner_id', 'in', self.signer_ids.partner_id.ids)])
        if not users:
            raise ValidationError("No valid users found for the signers.")
        sign_request = self.env['sign.request'].create({
            'name': self.template_id.name,
            'template_id': self.template_id.id,
            'data': self.template_id.data,
            'allowed_user_ids': [fields.Command.set(users.ids)],
            'validity': self.validity,
            'requester_ids': [fields.Command.create({
                'partner_id': signer.partner_id.id,
                'role_id': signer.role_id.id,
            }) for signer in self.signer_ids],
            'email_cc_ids': [fields.Command.set(self.contact_ids.ids)],
            'custom_subject': self.subject or False,
            'custom_message': self.message or False,
            'res_model': self.res_model,
            'res_id': self.res_id,
        })
        sign_request.send_sign_request_email()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Signature Request',
            'res_model': 'sign.request',
            'res_id': sign_request.id,
            'view_mode': 'form',
            'views': [[False, 'form']],
            'target': 'current',
        }

    def action_generate_sign(self):
        users = self.env['res.users'].sudo().search([('partner_id', 'in', self.signer_ids.partner_id.ids)])
        if not users:
            raise ValidationError("No valid users found for the signers.")
        sign_request = self.env['sign.request'].create({
            'name': self.template_id.name,
            'template_id': self.template_id.id,
            'data': self.template_id.data,
            'allowed_user_ids': [fields.Command.set(users.ids)],
            'validity': self.validity,
            'requester_ids': [
                fields.Command.create({
                    'partner_id': signer.partner_id.id,
                    'role_id': signer.role_id.id,
                }) for signer in self.signer_ids
            ],
            'res_model': self.res_model,
            'res_id': self.res_id,
        })
        return sign_request.action_sign()


class SignSigners(models.TransientModel):
    _name = 'sign.signers'
    _description = 'Sign Signers'

    role_id = fields.Many2one('sign.role', required=True)
    partner_id = fields.Many2one('res.partner')
    sign_generate_id = fields.Many2one('sign.generate')
    filtered_partner_ids = fields.Many2many('res.partner', compute='_compute_filtered_partner_ids')

    @api.depends('role_id')
    def _compute_filtered_partner_ids(self):
        """function for dynamic domain"""
        for rec in self:
            domain = rec.role_id.domain
            if domain:
                rec.filtered_partner_ids = rec.env['res.partner'].search(eval(domain))
            else:
                rec.filtered_partner_ids = rec.env['res.partner'].search([])
