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
from datetime import timedelta

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class MaintenanceRequest(models.Model):
    """Inherited model for extending maintenance and repair requests."""
    _inherit = 'maintenance.request'

    asset_id = fields.Many2one('asset.asset')
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True,
                                  default=lambda self: self.env.company.currency_id)
    expense = fields.Monetary(string="Expense")
    partner_id = fields.Many2one('res.partner', string="Repair partner")
    has_billed = fields.Boolean(default=False)
    stage_done = fields.Boolean(related='stage_id.done', store=True)
    has_warranty = fields.Boolean(default=False, compute="_compute_has_warranty")
    has_insurance = fields.Boolean(default=False, compute="_compute_has_insurance")
    is_reimburse = fields.Boolean(default=False, compute="_compute_has_insurance")
    is_scrap = fields.Boolean(default=False)
    invoiced_amount = fields.Monetary(string="Insurance Amount", compute="_compute_invoiced_amount")
    transaction_count = fields.Integer(string='Invoice', copy=False, compute='_compute_transaction_count')
    booking_id = fields.Many2one(string="Booking ID", comodel_name='asset.booking', copy=False)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        asset_id = self.env.context.get('default_asset_id')
        if asset_id:
            asset = self.env['asset.asset'].browse(asset_id)
            today = fields.Date.today()
            res['has_warranty'] = bool(
                asset.under_warranty
                and asset.warranty_end_date
                and asset.warranty_end_date >= today
            )
            res['has_insurance'] = bool(
                asset.under_insurance
                and asset.insurance_end_date
                and asset.insurance_end_date >= today
            )
        return res


    def _compute_transaction_count(self):
        """Function for computing the invoice count"""
        self.transaction_count = self.env['account.move'].search_count(
            [('repair_id', '=', self.id), ('move_type', 'in', ['in_invoice', 'out_invoice'])])

    def _compute_invoiced_amount(self):
        for rec in self:
            invoices = self.env['account.move'].sudo().search([('repair_id', '=', rec.id),('move_type', '=', 'out_invoice'),
                                                        ('state', '=', 'posted')])
            rec.invoiced_amount = sum(invoices.mapped('amount_total_signed'))

    @api.depends('asset_id')
    def _compute_has_warranty(self):
        """Function for checking Warranty period"""
        if self.asset_id.under_warranty and self.asset_id.warranty_end_date >= fields.Date.today():
            self.has_warranty = True
        else:
            self.has_warranty = False

    @api.depends('asset_id')
    def _compute_has_insurance(self):
        """Function for checking Warranty period"""
        if self.asset_id.under_insurance and self.asset_id.insurance_end_date >= fields.Date.today():
            self.has_insurance = True
            if self.asset_id.reimburse_after_invoice:
                self.is_reimburse = True
            else:
                self.is_reimburse = False
        else:
            self.has_insurance = False
            self.is_reimburse = False

    @api.onchange('stage_id')
    def _onchahange_stage_id(self):
        """Function for changing maintenance state"""
        if self.asset_id and self.stage_done == True:
            if self.maintenance_type == 'preventive':
                self.asset_id._message_log(
                    body=_(f"Maintenance completed for {self.asset_id.name}.")
                )
            if self.maintenance_type == 'corrective':
                self.asset_id._message_log(
                    body=_(f"Repair completed for {self.asset_id.name}.")
                )
            self.asset_id.is_maintenance = False
            self.asset_id.is_repair = False
            self.asset_id.last_maintenance_date = fields.Date.today()
            self.booking_id.state = 'done'

    @api.onchange('equipment_id')
    def _onchange_equipment_id(self):
        """Function for clearing asset and its related fields"""
        if self.equipment_id:
            self.asset_id = False
            self.partner_id = False
            self.expense = False

    @api.onchange('asset_id')
    def _onchange_asset_id(self):
        """Function for clearing equipment field"""
        if self.asset_id:
            self.equipment_id = False

    @api.model
    def create(self, vals):
        """If schedule_date is not provided → set to now"""
        schedule_date = vals.get('schedule_date')
        if schedule_date:
            schedule_date = fields.Datetime.to_datetime(schedule_date)
        else:
            schedule_date = fields.Datetime.now()
        vals['schedule_date'] = schedule_date
        record = super().create(vals)
        if self.asset_id:
            booking = self.env['asset.booking'].create_or_update_booking(
                asset=record.asset_id,
                date_from=schedule_date,
                date_to=schedule_date + timedelta(hours=record.duration),
                booking_type='maintenance',
                partner=record.partner_id,
                res_model=record._name,
                res_id=record.id
            )
            record.booking_id = booking.id
        return record

    def write(self, vals):
        res = super().write(vals)
        trigger_fields = {'asset_id', 'schedule_date', 'duration', 'partner_id'}

        if trigger_fields & set(vals):
            for rec in self:
                schedule_date = rec.schedule_date
                if schedule_date:
                    schedule_date = fields.Datetime.to_datetime(schedule_date)
                else:
                    schedule_date = fields.Datetime.now()

                if self.asset_id:
                    booking = self.env['asset.booking'].create_or_update_booking(
                        asset=rec.asset_id,
                        date_from=schedule_date,
                        date_to=schedule_date + timedelta(hours=rec.duration or 0),
                        booking_type='maintenance',
                        partner=rec.partner_id,
                        res_model=rec._name,
                        res_id=rec.id
                    )
                    rec.booking_id = booking.id
        return res

    def action_create_bill(self):
        """Button action for creating the bill for the repair"""
        if self.expense == 0:
            raise ValidationError(_('The expense is 0.'))
        repair_bill = self.env['account.move'].create({
            'ref': self.asset_id.name,
            'partner_id': self.partner_id.id,
            'move_type': 'in_invoice',
            'state': 'draft',
            'repair_id': self.id,
            'asset_id': False,
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': [fields.Command.create({
                'name': f"{self.asset_id.name}-Repair Bill",
                'move_type': 'in_invoice',
                'quantity': 1,
                'price_unit': self.expense,
                'price_subtotal': self.expense
            })]
        })
        self.asset_id._message_log(
            body=_(f"Bill created for {self.asset_id.name}. Amount: {self.expense}.")
        )
        self.has_billed = True

    def action_claim_insurance(self):
        """Button action for claiming insurance for the repair"""
        self.ensure_one()
        insurance_amount = self.env.context.get('insurance_amount', 0)
        is_reimburse = self.env.context.get('is_reimbursed', False)
        currency_id = self.env.context.get('currency_id', self.currency_id)
        if not is_reimburse and not self.has_billed:
            self.action_create_bill()
        repair_invoice = self.env['account.move'].create({
            'ref': self.asset_id.name,
            'partner_id': self.asset_id.insurance_name_id.partner_id.id,
            'move_type': 'out_invoice',
            'state': 'draft',
            'repair_id': self.id,
            'asset_id': False,
            'currency_id': currency_id,
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': [fields.Command.create({
                'name': f"{self.asset_id.name}-Insurance claim",
                'move_type': 'out_invoice',
                'quantity': 1,
                'price_unit': insurance_amount,
                'price_subtotal': insurance_amount,
            })]
        })

    def action_view_moves(self):
        """Function for viewing the invoice"""
        return {
            'name': _('Invoices / Bills'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [('repair_id', '=', self.id), ('move_type', 'in', ['in_invoice', 'out_invoice'])],
        }

    def action_scrap(self):
        """Button action for scrapping the repair asset"""
        self.asset_id.status = 'disposed'
        self.asset_id.is_repair = False
        self.is_scrap = True
        action_scrap = self.env['asset.sell.dispose'].sudo().create({
            'asset_asset_id': self.asset_id.id,
            'asset_action': 'dispose',
            'loss_account_id': self.asset_id.asset_loss_account_id.id,
            'date': fields.Date.today(),
            'note': "Scrapped after repair",
            'disposal_type': 'scrap',
        })
        if self.asset_id.is_entry:
            action_scrap.action_dispose()

    def action_claim_insurance_wizard(self):
        balance = self.expense - self.invoiced_amount
        return {
            'name': _('Claim Insurance'),
            'view_mode': 'form',
            'res_model': 'asset.insurance',
            'type': 'ir.actions.act_window',
            'context': {
                'default_asset_id': self.asset_id.id,
                'default_total_amount': self.expense,
                'default_repair_id': self.id,
                'default_reimburse_after_invoice': self.is_reimburse,
                'default_insurance_amount': balance,
                'default_invoiced_amount': self.invoiced_amount,
                'default_expense': self.expense,
            },
            'target': 'new'
        }
