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


class AccountMove(models.Model):
    _inherit = 'account.move'

    three_way_match = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No'),
        ('exception', 'Exception')
    ], string="Should Be Paid", compute="_compute_three_way_match", store=True, readonly=False)

    three_way_matching_enabled = fields.Boolean(
        compute='_compute_three_way_matching_enabled',
        string="3-Way Matching Enabled"
    )

    @api.depends_context('company')
    def _compute_three_way_matching_enabled(self):
        enabled = self.env['ir.config_parameter'].sudo().get_param('cyllo_purchase.three_way_matching')
        for move in self:
            move.three_way_matching_enabled = bool(enabled)

    @api.depends('invoice_line_ids.three_way_match_status')
    def _compute_three_way_match(self):
        for move in self:
            if move.move_type not in ('in_invoice', 'in_refund'):
                move.three_way_match = False
                continue

            lines = move.invoice_line_ids.filtered(lambda l: l.display_type not in ('line_section', 'line_note') and l.product_id)
            if not lines:
                move.three_way_match = 'no'
                continue

            statuses = set(lines.mapped('three_way_match_status'))

            if 'exception' in statuses:
                move.three_way_match = 'exception'
            elif len(statuses) > 1:
                # mix of 'yes' and 'no'
                move.three_way_match = 'exception'
            elif 'yes' in statuses:
                move.three_way_match = 'yes'
            else:
                move.three_way_match = 'no'


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    three_way_match_status = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No'),
        ('exception', 'Exception')
    ], string="Line 3-Way Match Status", compute="_compute_three_way_match_status", store=True)

    @api.depends('quantity', 'purchase_line_id.qty_received', 'purchase_line_id.qty_invoiced', 'purchase_line_id.product_qty')
    def _compute_three_way_match_status(self):
        for line in self:
            if line.display_type in ('line_section', 'line_note') or not line.product_id:
                line.three_way_match_status = False
                continue

            po_line = line.purchase_line_id
            if not po_line:
                # directly created bill, no PO -> no received qty -> no
                line.three_way_match_status = 'no'
            else:
                received_qty = po_line.qty_received
                invoiced_qty = po_line.qty_invoiced
                ordered_qty = po_line.product_qty

                # yes case: billed qty <= received
                if invoiced_qty <= received_qty:
                    line.three_way_match_status = 'yes'
                # no case: no received qty and billed <= ordered
                elif received_qty == 0 and invoiced_qty <= ordered_qty:
                    line.three_way_match_status = 'no'
                # exception case: billed > received
                else:
                    line.three_way_match_status = 'exception'
