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


class FrontdeskEnquiry(models.Model):
    _name = 'frontdesk.enquiry'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Front Desk Enquiry'
    _order = 'enquiry_date desc, id desc'

    name = fields.Char(
        string='Enquiry Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New')
    )
    visitor_name = fields.Char(string='Visitor Name', required=True, tracking=True)
    phone = fields.Char(string='Phone', tracking=True)
    email = fields.Char(string='Email', tracking=True)
    company = fields.Char(string='Company / Organization', tracking=True)

    station_id = fields.Many2one(
        'frontdesk.frontdesk',
        string='Station',
        required=True,
        tracking=True
    )
    handled_by = fields.Many2one(
        'hr.employee',
        string='Handled By',
        help='Staff member who attended to this enquiry',
        tracking=True
    )

    enquiry_date = fields.Datetime(
        string='Enquiry Date',
        default=fields.Datetime.now,
        readonly=True,
        tracking=True
    )

    enquiry_type = fields.Selection([
        ('general', 'General Information'),
        ('product', 'Product / Service'),
        ('pricing', 'Pricing & Quotation'),
        ('support', 'Support / Complaint'),
        ('career', 'Career / Recruitment'),
        ('other', 'Other'),
    ], string='Enquiry Type', required=True, default='general', tracking=True)

    subject = fields.Char(string='Subject', required=True, tracking=True)
    description = fields.Text(string='Enquiry Details')

    state = fields.Selection([
        ('new', 'New'),
        ('in_progress', 'In Progress'),
        ('closed', 'Closed'),
        ('lost', 'Lost'),
    ], string='Status', default='new', required=True, tracking=True, group_expand=True)

    priority = fields.Selection([
        ('0', 'Normal'),
        ('1', 'High'),
        ('2', 'Urgent'),
    ], string='Priority', default='0')

    # Conversion links
    visitor_id = fields.Many2one(
        'frontdesk.visitor',
        string='Linked Visitor',
        readonly=True,
        copy=False,
        tracking=True,
        help='Visitor record automatically created when this enquiry was saved.'
    )

    partner_id = fields.Many2one(
        'res.partner',
        string='Linked Contact',
        tracking=True,
        help='Customer / partner matched or created from this enquiry.'
    )


    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'frontdesk.enquiry') or _('New')
        records = super().create(vals_list)
        for rec in records:
            # Skip if a visitor is already linked (e.g. created programmatically)
            if rec.visitor_id:
                continue
            visitor = self.env['frontdesk.visitor'].create({
                'visitor_name': rec.visitor_name,
                'visitor_type': 'enquiry',
                'phone': rec.phone,
                'email': rec.email,
                'company': rec.company,
                'station_id': rec.station_id.id,
                'host_id': rec.handled_by.id if rec.handled_by else False,
                'state': 'planned',
            })
            rec.visitor_id = visitor.id
            visitor.enquiry_id = rec.id
            rec._message_log(
                body=_(
                    "Visitor record auto-created: <a href='#' data-oe-model='frontdesk.visitor' data-oe-id='%d'>%s</a>") % (
                         visitor.id, visitor.name)
            )
            visitor._message_log(
                body=_(
                    "Linked to enquiry: <a href='#' data-oe-model='frontdesk.enquiry' data-oe-id='%d'>%s</a>") % (
                         rec.id, rec.name)
            )
        return records

    def action_in_progress(self):
        for rec in self:
            if rec.state != 'new':
                raise UserError(_('Only new enquiries can be moved to In Progress.'))
            rec.write({'state': 'in_progress'})
            rec._message_log(body=_("Enquiry marked as In Progress."))

    def action_close(self):
        for rec in self:
            if rec.state in ('lost',):
                raise UserError(_('Cannot close a  lost enquiry.'))
            rec.write({'state': 'closed'})
            rec._message_log(body=_("Enquiry closed."))

    def action_mark_lost(self):
        for rec in self:
            rec.write({'state': 'lost'})
            rec._message_log(body=_("Enquiry marked as lost."))

    def action_reset_new(self):
        for rec in self:
            rec.write({'state': 'new'})
            rec._message_log(body=_("Enquiry reset to New."))

    def action_convert_to_visitor(self):
        """Convert this enquiry into a frontdesk.visitor (planned visit)."""
        self.ensure_one()
        if self.visitor_id:
            raise UserError(_("This enquiry has already been converted to a visitor record."))

        # Try to match or create a res.partner
        if not self.partner_id:
            partner = self.env['res.partner']
            if self.email:
                partner = partner.search([('email', '=', self.email)], limit=1)
            if not partner and self.phone:
                partner = self.env['res.partner'].search(
                    ['|', ('phone', '=', self.phone), ('mobile', '=', self.phone)], limit=1
                )
            if not partner and self.visitor_name:
                partner = self.env['res.partner'].search([('name', '=', self.visitor_name)], limit=1)

            if not partner:
                partner_vals = {
                    'name': self.visitor_name,
                    'email': self.email or False,
                    'phone': self.phone or False,
                }
                if self.company:
                    company_partner = self.env['res.partner'].search([
                        ('name', '=', self.company),
                        ('is_company', '=', True)
                    ], limit=1)
                    if not company_partner:
                        company_partner = self.env['res.partner'].create({
                            'name': self.company,
                            'is_company': True,
                        })
                    partner_vals['parent_id'] = company_partner.id
                partner = self.env['res.partner'].create(partner_vals)

            self.partner_id = partner.id

        # Create the visitor record
        visitor = self.env['frontdesk.visitor'].create({
            'visitor_name': self.visitor_name,
            'phone': self.phone,
            'email': self.email,
            'company': self.company,
            'station_id': self.station_id.id,
            'state': 'planned',
        })

        self.write({
            'visitor_id': visitor.id,
            'state': 'converted',
        })
        self._message_log(
            body=_("Enquiry converted to visitor: <a href='#' data-oe-model='frontdesk.visitor' data-oe-id='%d'>%s</a>") % (visitor.id, visitor.name)
        )

        # Open the newly created visitor form
        return {
            'name': _('Visitor'),
            'type': 'ir.actions.act_window',
            'res_model': 'frontdesk.visitor',
            'res_id': visitor.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_visitor(self):
        self.ensure_one()
        if not self.visitor_id:
            raise UserError(_("No visitor record linked to this enquiry."))
        return {
            'name': _('Visitor'),
            'type': 'ir.actions.act_window',
            'res_model': 'frontdesk.visitor',
            'res_id': self.visitor_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
