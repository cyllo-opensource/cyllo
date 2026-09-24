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
from datetime import date
from odoo import fields, models

class ResPartner(models.Model):
    """
    Inherit res.partner to manage follow-ups for overdue invoices.
    This includes adding a computed field to check follow-ups and a method to change follow-up actions.
    """
    _inherit = 'res.partner'

    move_ids = fields.One2many(
        'account.move', 'partner_id',
        string="Invoice Details",
        domain=([('payment_state', '!=', 'paid'),
                 ('state', '=', 'posted'),
                 ('invoice_date_due', '<',
                  date.today())]),
        readonly=True,
        help="List of unpaid and posted invoices with due dates earlier than today."
    )
    check_followups = fields.Boolean(
        compute='_compute_check_followups',
        help="Indicates if follow-up checks have been performed for this partner."
    )

    def _compute_check_followups(self):
        """
        Compute the `check_followups` field.
        For each partner, this method iterates through overdue invoices (`move_ids`).
        If a matching follow-up line exists for the number of days overdue and no next follow-up is set,
        it assigns the follow-up line to the invoice.
        """
        for rec in self:
            move_ids = rec.move_ids
            for move_id in move_ids:
                due_day = (date.today() - move_id.invoice_date_due).days
                follow_ups = self.env['accounting.followup.line'].search(
                    [('due_date', '=', due_day)])
                if follow_ups:
                    if follow_ups[
                        0].id != move_id.last_follow_up_id.id and not move_id.next_follow_up_id:
                        move_id.write({'next_follow_up_id': follow_ups[0].id})
            rec.write({'check_followups': True})

    def change_followup_action(self, move_id):
        """
        Change the follow-up action for the given invoice (`move_id`).
        If the follow-up line has a configured email template, it sends an email.
        The `next_follow_up_id` is cleared, and `last_follow_up_id` is updated to the current follow-up.

        :param move_id: The account move (invoice) for which to change the follow-up action.
        """
        for move in move_id:
            follow_up = move.next_follow_up_id
            if follow_up.send_mail:
                mail_template = follow_up.mail_template_id
                mail_template.sudo().with_context({'move_id': move}).send_mail(
                    self.id, force_send=True)
                move.write({
                    'next_follow_up_id': False,
                    'last_follow_up_id': follow_up.id
                })

    def _execute_followup(self):
        """Execute this function-based cron job"""
        lines = self.env['account.move'].search([('next_follow_up_id', '!=', False)])
        self.change_followup_action(lines)
