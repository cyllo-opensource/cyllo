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
from odoo import  api, fields, models
from odoo.exceptions import UserError


class ApprovalTransferWizard(models.TransientModel):
    _name = 'approval.transfer.wizard'
    _description = "Transfer Approval Wizard"

    request_id = fields.Many2one(
        'approval.request',
        required=True,
    )
    user_id = fields.Many2one(
        'res.users',
        string="Transfer To",
        required=True,
    )
    current_user_id = fields.Many2one('res.users')
    note = fields.Text(
        'Reason',
        required=True,
        help="Reason for transferring the approval."
    )
    approval_user_ids = fields.Many2many(
        'res.users',
        compute='_compute_approval_user_ids',
    )

    @api.depends("user_id")
    def _compute_approval_user_ids(self):
        approval_user_group = self.env.ref(
            'cyllo_approval.group_approval_user', raise_if_not_found=False
        )
        approval_manager_group = self.env.ref(
            'cyllo_approval.group_approval_manager', raise_if_not_found=False
        )
        group_ids = [g.id for g in (approval_user_group, approval_manager_group) if g]

        users = self.env['res.users'].search([
            ('groups_id', 'in', group_ids),
            ('id', '!=', self.env.user.id),
        ]) if group_ids else self.env['res.users']

        for wizard in self:
            wizard.approval_user_ids = users

    def action_transfer_approval(self):
        """Transfer approval from one user to another."""
        self.ensure_one()
        request = self.request_id
        if request.approver_id != self.current_user_id:
            raise UserError(
                "Only the current approver can transfer this approval.")
        request.write({
            'approver_id': self.user_id.id,
            'note': self.note,
        })
        model = request.res_model
        approval_record = self.env[model].browse(request.res_id)
        approval_record.write({
            'x_current_approver_id': self.user_id.id,
        })
        request._message_log(
            body=f"Approval transferred from {self.current_user_id.name} "
                 f"to {self.user_id.name}. Reason: {self.note}"
        )
        return {'type': 'ir.actions.act_window_close'}
