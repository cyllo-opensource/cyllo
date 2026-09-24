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
from dateutil.relativedelta import relativedelta

from odoo import _, api, models, fields
from odoo.exceptions import UserError


class AssetLease(models.Model):
    """Model for the asset lease"""
    _name = 'asset.lease'
    _description = 'Lease Assets'
    _rec_name = 'asset_id'
    _inherit = ['mail.thread']

    asset_id = fields.Many2one(
        'asset.asset',
        required=True,
        help='Asset selected for leasing.'
    )
    start_date = fields.Datetime(
        string='Period',
        required=True,
        tracking=True,
        help="Lease start date and time. Select an asset before setting the period. "
             "The selected dates must be after the asset purchase date."
    )
    end_date = fields.Datetime(
        string='End',
        required=True,
        tracking=True,
        help='Lease end date and time. It must be greater than the start date.'
    )
    customer_id = fields.Many2one(
        'res.partner',
        required=True,
        tracking=True,
        help='Customer leasing the asset.'
    )
    email = fields.Char(
        related='customer_id.email',
        help='Email address of the customer.'
    )
    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
        help='Company associated with this lease.'
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        help='Currency used by the company.'
    )
    status = fields.Selection(
        [
            ('draft', 'Draft'),
            ('lease', 'Lease'),
            ('return', 'Return'),
            ('cancel', 'Cancel')
        ],
        default='draft',
        tracking=True,
        copy=False,
        help='Current status of the lease.'
    )
    reservation_id = fields.Many2one(
        'asset.reservation',
        help='Reservation linked to this lease.'
    )
    lease_amount = fields.Float(
        string='Amount',
        required=True,
        help='Lease amount charged to the customer.'
    )
    is_return = fields.Boolean(
        copy=False,
        help='Indicates whether the asset has been returned.'
    )
    is_invoice = fields.Boolean(
        copy=False,
        help='Indicates whether an invoice has been created for this lease.'
    )
    active = fields.Boolean(
        default=True,
        help='Determines whether the lease record is active.'
    )
    asset_ids = fields.Many2many(
        'asset.asset',
        compute='_compute_asset_ids',
        help='Available assets for the selected lease period.'
    )
    booking_id = fields.Many2one(
        'asset.booking',
        string='Booking ID',
        copy=False,
        help='Booking record linked to this lease.'
    )
    availability_warning = fields.Html(
        readonly=True,
        help='Displays asset availability warnings for the selected date range.'
    )

    @api.depends('company_id')
    def _compute_asset_ids(self):
        """Function for showing reserved assets only to user"""
        for record in self:
            if (self.env.user.has_group('account.group_account_manager') or
                    self.env.user.has_group('cyllo_asset_management.group_cyllo_asset_admin')):
                record.asset_ids = self.env['asset.asset'].search([])
            elif self.env.user.has_group('cyllo_asset_management.group_cyllo_asset_users'):
                record.asset_ids = self.env['asset.reservation'].search([('employee_id.user_id', '=', self.env.user.id),
                                                                         ('status', '=', 'reserve')]).mapped('asset_id')

    @api.onchange('lease_amount')
    def _onchange_lease_amount(self):
        """Function for checking the lease amount"""
        if self.lease_amount and self.lease_amount < 0:
            self.lease_amount = abs(self.lease_amount)

    @api.onchange('start_date', 'end_date')
    def _onchange_lease_date(self):
        """Function for checking the start and end date"""
        purchase_date = self.sudo().asset_id.date
        if self.start_date and self.end_date:
            if self.end_date < self.start_date:
                raise UserError(_('The End Date is greater than the Start Date'))
            elif (self.start_date.date() < purchase_date) or (self.end_date.date() < purchase_date):
                raise UserError(
                    _(f'The Asset id Purchased on {purchase_date}.The Start Date and End Date should '
                      f'be greater than the Purchase Date'))
            if self.reservation_id:
                reserved_date = self.reservation_id.start_date
                if self.start_date.date() < reserved_date:
                    raise UserError(
                        _(f'The Asset is Reserved on {reserved_date}. The Start Date should be greater than '
                          f'the Reserved start Date'))

    @api.model
    def create(self, vals):
        record = super().create(vals)

        booking = self.env['asset.booking'].create_or_update_booking(
            asset=record.asset_id,
            date_from=fields.Datetime.to_datetime(record.start_date),
            date_to=fields.Datetime.to_datetime(record.end_date) + relativedelta(days=1),
            booking_type='lease',
            partner=record.customer_id,
            res_model=record._name,
            res_id=record.id
        )
        record.booking_id = booking.id
        return record

    def write(self, vals):
        res = super().write(vals)
        for rec in self:
            if {'asset_id', 'start_date', 'end_date'} & set(vals):
                booking = self.env['asset.booking'].create_or_update_booking(
                    asset=rec.asset_id,
                    date_from=fields.Datetime.to_datetime(rec.start_date),
                    date_to=fields.Datetime.to_datetime(rec.end_date) + relativedelta(days=1),
                    booking_type='rental',
                    partner=rec.customer_id,
                    res_model=rec._name,
                    res_id=rec.id
                )
                rec.booking_id = booking.id
        return res

    def unlink(self):
        """Function for unlink the lease records"""
        for rec in self:
            if rec.status == 'lease':
                raise UserError(_('You cannot delete the record that is in leased state.'))
        else:
            self.asset_id.is_lease = False
            return super().unlink()

    @api.onchange('asset_id', 'start_date', 'end_date')
    def _onchange_availability_warning(self):
        """Check the availability of assets"""
        self.availability_warning = False
        if not self.asset_id or not self.start_date or not self.end_date:
            return
        messages = []
        overlap_domain = [
            ('asset_id', '=', self.asset_id.id),
            ('status', 'not in', ['cancel', 'draft']),
            ('start_date', '<=', self.end_date),
            ('end_date', '>=', self.start_date),
        ]
        reservations = self.env['asset.reservation'].sudo().search(overlap_domain)
        for rec in reservations:
            messages.append(
                f"Reserved from {rec.start_date} to {rec.end_date}"
            )
        leases = self.env['asset.lease'].sudo().search(overlap_domain)
        for rec in leases:
            messages.append(
                f"Leased from {rec.start_date} to {rec.end_date}"
            )
        rentals = self.env['asset.rental'].sudo().search(overlap_domain)
        for rec in rentals:
            messages.append(
                f"Rented from {rec.start_date} to {rec.end_date}"
            )
        if messages:
            self.availability_warning = "<br/>".join(messages)


    def action_create_lease(self):
        """Button action creating lease based only on date availability"""
        asset_id = self.sudo().asset_id
        if not asset_id.is_lease_asset:
            raise UserError(_('You cannot complete this operation, the related asset is not a lease asset.'))
        if asset_id.is_sell or asset_id.is_dispose:
            raise UserError(_('You cannot complete this operation, the related asset is either sold or disposed.'))
        if self.lease_amount is None:
            raise UserError(_('You cannot complete this operation, please specify the lease amount.'))
        if self.lease_amount == 0:
            raise UserError(_('You cannot complete this operation, lease amount cannot be zero.'))
        overlap_domain = [
            ('asset_id', '=', self.asset_id.id),
            ('status', 'not in', ['cancel', 'draft']),
            ('start_date', '<=', self.end_date),
            ('end_date', '>=', self.start_date),
        ]
        reservation_conflict = self.env['asset.reservation'].sudo().search(overlap_domain, limit=1)
        lease_conflict = self.env['asset.lease'].sudo().search(overlap_domain, limit=1)
        rental_conflict = self.env['asset.rental'].sudo().search(overlap_domain, limit=1)
        if reservation_conflict or lease_conflict or rental_conflict:
            raise UserError(_(
                "You cannot complete this operation. The asset is already reserved, leased, or rented "
                "for the selected date range."
            ))
        self.booking_id.state = 'confirmed'
        self.status = 'lease'
        context = {
            'asset': asset_id.name,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'customer': self.customer_id.name
        }
        template = self.env.ref('cyllo_asset_management.mail_template_asset_leasing',raise_if_not_found=False)
        if template:
            template.with_context(**context).send_mail(
                res_id=self.id,
                email_values={'email_to': self.email},
                force_send=True
            )
        asset_id.write({
            'status' : 'leased',
            'is_lease' : True,
        })
        if self.reservation_id:
            asset_id.status = 'reserved'
            self.reservation_id.write({'status': 'lease'})
        self.env['account.move'].create({
            'asset_id': False,
            'ref': asset_id.name,
            'partner_id': self.customer_id.id,
            'move_type': 'out_invoice',
            'state': 'draft',
            'lease_id': self.id,
            'invoice_line_ids': [fields.Command.create({
                'name': f"{asset_id.name}-Lease",
                'price_unit': self.lease_amount,
            })]
        })
        self.is_invoice = True



    def action_view_invoice(self):
        """Function for viewing the lease invoice"""
        lease_invoice = self.env['account.move'].search([('ref', '=', self.asset_id.name), ('lease_id', '=', self.id)])
        if len(lease_invoice) > 1:
            return {
                'name': 'Invoice',
                'view_mode': 'tree, form',
                'res_model': 'account.move',
                'type': 'ir.actions.act_window',
                'domain': [('id', 'in', lease_invoice.ids)],
            }
        else:
            return {
                'name': 'Invoice',
                'view_mode': 'form',
                'res_id': lease_invoice.id,
                'res_model': 'account.move',
                'type': 'ir.actions.act_window',
            }

    def action_return_asset(self):
        """Button action returning the leased assets"""
        asset_id = self.sudo().asset_id
        invoice = self.env['account.move'].search([('lease_id', '=', self.id), ('payment_state', '!=', 'paid')])
        if invoice:
            raise UserError(
                _('You cannot complete this operation, The invoice is not paid'))
        else:
            if not self.booking_id:
                raise UserError(_('No booking found for this rental.'))
            self.booking_id.state = 'done'
            self.is_return = True
            self.status = 'cancel'
            asset_id.is_lease = False
            if self.reservation_id:
                if self.reservation_id.end_date > fields.date.today():
                    asset_id.is_reserve = True
                    self.reservation_id.write({
                        'status': 'reserve'})
                else:
                    asset_id.is_reserve = False
                    self.reservation_id.write({
                        'status': 'cancel'})
            if asset_id.is_reserve == True:
                asset_id.status = 'reserved'
            elif asset_id.is_confirm == True:
                asset_id.status = 'running'
            else:
                asset_id.status = 'draft'

    def action_reset_to_draft(self):
        """Function for reset the leased assets to the draft state"""
        if self.asset_id.status in ('sell', 'disposed', 'cancel', 'lost'):
            raise UserError(_(f'You cannot reset to draft.The related asset is in {self.asset_id.status} state.'))
        self.status = 'draft'

    def _send_lease_asset_return_reminder_mail(self):
        """Function for sending mails to the customer regarding the lease"""
        lease_asset = self.search([('status', '=', 'lease')])
        for asset in lease_asset:
            remainder_date = asset.end_date + relativedelta(days=-3)
            if fields.Date.today() == remainder_date:
                context = {
                    'asset': asset.asset_id.name,
                    'end_date': asset.end_date,
                    'customer': asset.customer_id.name
                }
                template = self.env.ref(
                    'cyllo_asset_management.mail_template_leased_assent_return_reminder',
                    raise_if_not_found=False)
                email_values = {
                    'email_to': asset.customer_id.email
                }
                template.with_context(**context).send_mail(res_id=asset.id, email_values=email_values, force_send=True)
