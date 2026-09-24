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
from dateutil.relativedelta import relativedelta
from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_is_zero, float_round


class MrpWipAccountingWizard(models.TransientModel):
    _name = 'mrp.wip.accounting.wizard'
    _description = 'Post WIP Accounting Entry'

    production_id = fields.Many2one('mrp.production', string="Manufacturing Order", required=True)
    company_id = fields.Many2one('res.company', string="Company", required=True)
    journal_id = fields.Many2one('account.journal', string="Journal", required=True, check_company=True)
    reference = fields.Char(string="Reference", required=True)
    date = fields.Date(string="Date", default=fields.Date.context_today, required=True)
    reversal_date = fields.Date(string="Reversal Date", required=True)
    line_ids = fields.One2many('mrp.wip.accounting.wizard.line', 'wizard_id', string="WIP Entry Lines")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        production_id = res.get('production_id') or self.env.context.get('default_production_id')
        if production_id:
            production = self.env['mrp.production'].browse(production_id)

            if production.state in ('to_close', 'done', 'cancel'):
                component_cost = 0.0
                overhead_cost = 0.0
            else:
                # Calculate Component Cost
                component_cost = sum(
                    move.product_id.uom_id._compute_price(move.product_id.standard_price, move.product_uom) *
                    (move.product_uom_qty if move.state != 'done' else move.quantity)
                    for move in production.move_raw_ids.filtered(lambda m: m.state != 'cancel' and not m.scrapped)
                )

                # Calculate Overhead Cost
                overhead_cost = 0.0
                for workorder in production.workorder_ids:
                    wo_duration = workorder.get_duration()
                    expected_cost = (workorder.duration_expected / 60.0) * (workorder.costs_hour or workorder.workcenter_id.costs_hour)
                    current_cost = (wo_duration / 60.0) * (workorder.costs_hour or workorder.workcenter_id.costs_hour)
                    is_workorder_started = not float_is_zero(wo_duration, precision_digits=2)
                    if is_workorder_started:
                        real_cost = current_cost
                    elif workorder.operation_id:
                        operation = workorder.operation_id
                        capacity = operation.workcenter_id._get_capacity(production.product_id)
                        operation_cycle = float_round(production.product_uom_qty / capacity, precision_rounding=1, rounding_method='UP')
                        bom_duration_expected = (operation_cycle * operation.time_cycle * 100.0 / operation.workcenter_id.time_efficiency) + \
                            operation.workcenter_id._get_expected_duration(production.product_id)
                        real_cost = expected_cost / (workorder.duration_expected or 1) * bom_duration_expected
                    else:
                        real_cost = expected_cost
                    overhead_cost += real_cost

            company = production.company_id
            res.update({
                'production_id': production.id,
                'company_id': company.id,
                'journal_id': company.wip_journal_id.id,
                'reference': _("Manufacturing WIP - %s") % production.name,
                'date': fields.Date.context_today(self),
                'reversal_date': fields.Date.context_today(self) + relativedelta(days=1),
            })

            lines = []
            # WIP Account (Debit)
            if company.wip_account_id:
                lines.append((0, 0, {
                    'account_id': company.wip_account_id.id,
                    'label': _("Manufacturing WIP - %s") % production.name,
                    'debit': component_cost + overhead_cost,
                    'credit': 0.0,
                }))

            # Stock Valuation Account (Credit for components)
            stock_valuation_account = production.product_id.categ_id.property_stock_valuation_account_id
            if stock_valuation_account:
                lines.append((0, 0, {
                    'account_id': stock_valuation_account.id,
                    'label': _("WIP - Component Value"),
                    'debit': 0.0,
                    'credit': component_cost,
                }))

            # WIP Overhead Account (Credit for overhead)
            if company.wip_overhead_account_id:
                lines.append((0, 0, {
                    'account_id': company.wip_overhead_account_id.id,
                    'label': _("WIP - Overhead"),
                    'debit': 0.0,
                    'credit': overhead_cost,
                }))

            res['line_ids'] = lines
        return res

    def action_post_wip(self):
        self.ensure_one()
        # Security check
        if not self.env.user.has_group('mrp.group_mrp_manager'):
            raise UserError(_("Only Manufacturing Managers can post WIP entries."))

        # Check line existence
        if not self.line_ids:
            raise UserError(_("You must have at least one line to post."))

        # Balance check
        total_debit = sum(line.debit for line in self.line_ids)
        total_credit = sum(line.credit for line in self.line_ids)
        if not self.company_id.currency_id.is_zero(total_debit - total_credit):
            raise UserError(_("The WIP entry must be balanced. Total Debit must equal Total Credit."))

        # Create the account.move entry
        move_vals = {
            'journal_id': self.journal_id.id,
            'ref': self.reference,
            'date': self.date,
            'move_type': 'entry',
            'production_id': self.production_id.id,
            'line_ids': [
                (0, 0, {
                    'account_id': line.account_id.id,
                    'name': line.label or self.reference,
                    'debit': line.debit,
                    'credit': line.credit,
                }) for line in self.line_ids
            ]
        }

        move = self.env['account.move'].create(move_vals)
        move.action_post()

        # Generate draft reversal entry
        reversal_vals = {
            'ref': _('Reversal of: %s') % self.reference,
            'date': self.reversal_date,
            'journal_id': self.journal_id.id,
            'auto_post': 'no',
        }

        reversal_move = move._reverse_moves([reversal_vals], cancel=False)
        reversal_move.write({
            'production_id': self.production_id.id,
            'ref': _('Reversal of: %s') % self.reference,
        })
        for line in reversal_move.line_ids:
            if line.name:
                line.name = _('Reversal of: %s') % line.name

        return {'type': 'ir.actions.act_window_close'}


class MrpWipAccountingWizardLine(models.TransientModel):
    _name = 'mrp.wip.accounting.wizard.line'
    _description = 'WIP Entry Line'

    wizard_id = fields.Many2one('mrp.wip.accounting.wizard', ondelete="cascade", required=True)
    account_id = fields.Many2one('account.account', string="Account", required=True)
    label = fields.Char(string="Label")
    debit = fields.Monetary(string="Debit", default=0.0)
    credit = fields.Monetary(string="Credit", default=0.0)

    company_id = fields.Many2one('res.company', related="wizard_id.company_id", readonly=True)
    currency_id = fields.Many2one('res.currency', related="company_id.currency_id", readonly=True)
