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
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ApprovalRequestWizard(models.TransientModel):
    _name = 'approval.request.wizard'
    _description = 'Approval Request Confirmation'

    rule_id = fields.Many2one(
        'approval.rule',
        required=True
    )
    line_id = fields.Many2one(
        'approval.rule.line',
        string='Approval Level',
        help="The level the request is going to be sent to."
    )
    res_model = fields.Char(
        required=True
    )
    res_id = fields.Integer(
        required=True
    )
    level_info = fields.Char(
        string='Approval Chain',
        compute='_compute_level_info',
        help="The levels the document has to go through."
    )
    approver_name = fields.Char(
        string='Next Approver',
        compute='_compute_level_info'
    )

    @api.depends('rule_id', 'line_id')
    def _compute_level_info(self):
        for wizard in self:
            levels = wizard.rule_id._get_levels() if wizard.rule_id \
                else wizard.env['approval.rule.line']
            wizard.level_info = ' → '.join(
                level.approver_name for level in levels) or False
            line = wizard._get_target_line()
            wizard.approver_name = line.approver_name if line else False

    def _get_target_line(self):
        """The level the request must be created for."""
        self.ensure_one()
        if self.line_id:
            return self.line_id
        if not self.rule_id:
            return self.env['approval.rule.line']
        return self.rule_id._get_pending_level(self.res_model, self.res_id)

    def action_request_approval(self):
        """Create the approval request for the first pending level."""
        self.ensure_one()
        line = self._get_target_line()
        if not line:
            raise UserError(_(
                "Rule '%s' has no approval level left to request."
            ) % self.rule_id.name)
        Request = self.env['approval.request'].sudo()
        Request.create(Request._prepare_level_request(
            self.rule_id, line, self.res_model, self.res_id,
            requested_by=self.env.user,
        ))
        return {'type': 'ir.actions.act_window_close'}
