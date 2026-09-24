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
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AssetInsurance(models.TransientModel):
    """ Wizard model for asset insurance claiming"""
    _name = 'asset.insurance'
    _description = 'Asset Insurance'

    asset_id = fields.Many2one('asset.asset', string='Asset ID', required=True, readonly=True)
    repair_id = fields.Many2one('maintenance.request', string='Repair ID', required=True)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True,
                                  default=lambda self: self.env.company.currency_id)
    claiming_currency_id = fields.Many2one('res.currency', string='Currency',
                                           default=lambda self: self.env.company.currency_id)
    total_amount = fields.Monetary(string="Total Repair Cost", readonly=True)
    insurance_amount = fields.Monetary(string="Claiming amount")
    reimburse_after_invoice = fields.Boolean(default=False)
    invoiced_amount = fields.Monetary()
    expense = fields.Monetary()

    @api.constrains('insurance_amount')
    def _check_insurance_amount(self):
        """Function for checking the percentage amount"""
        if self.insurance_amount > self.expense or self.insurance_amount < 0:
            raise UserError(
                _('Please enter a valid insurance amount'))
        if self.insurance_amount > self.expense - self.invoiced_amount:
            raise UserError(
                _('The Total invoiced Amount exceeds expense'))

    def action_claim(self):
        """Function for calling insurance claim"""
        self.asset_id._message_log(
            body=_(f"Insurance claimed for {self.asset_id.name}. Amount: {self.insurance_amount}.")
        )
        return self.repair_id.with_context(
            currency_id=self.claiming_currency_id.id,
            insurance_amount=self.insurance_amount,
            is_reimbursed=self.reimburse_after_invoice,
        ).action_claim_insurance()
