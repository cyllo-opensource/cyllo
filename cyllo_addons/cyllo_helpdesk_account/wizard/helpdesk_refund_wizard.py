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
from odoo import models, fields, _


class HelpdeskRefundWizard(models.TransientModel):
    _name = 'helpdesk.refund.wizard'
    _description = 'Helpdesk Refund Wizard'

    ticket_id = fields.Many2one('helpdesk.ticket', string="Helpdesk Ticket", required=True)
    customer_id = fields.Many2one('res.partner', string="Customer")
    invoice_id = fields.Many2one(
        'account.move',
        string="Invoice",
        domain="[('move_type', '=', 'out_invoice'), ('state', '=', 'posted'), ('partner_id', 'child_of', customer_id)]"
    )
    journal_id = fields.Many2one(
        'account.journal',
        string="Journal",
        domain="[('type', '=', 'sale')]",
        required=True
    )
    date = fields.Date(
        string="Reversal Date",
        default=fields.Date.context_today,
        required=True
    )
    reason = fields.Char(string="Reason", default="Refund from Helpdesk")

    def action_confirm(self):
        """Create a credit note from the selected invoice or create a new credit note."""
        self.ensure_one()
        if self.invoice_id:
            credit_notes = self.invoice_id._reverse_moves(
                [{
                    'date': self.date,
                    'journal_id': self.journal_id.id,
                    'ref': self.reason,
                }],
                cancel=False,
            )
        else:
            # Create a new credit note
            credit_notes = self.env['account.move'].create({
                'move_type': 'out_refund',
                'partner_id': self.customer_id.id,
                'invoice_date': self.date,
                'date': self.date,
                'journal_id': self.journal_id.id,
                'ref': self.reason,
                'helpdesk_ticket_id': self.ticket_id.id,
            })

        credit_notes.write({
            'helpdesk_ticket_id': self.ticket_id.id,
        })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Credit Note'),
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': credit_notes.id,
        }
