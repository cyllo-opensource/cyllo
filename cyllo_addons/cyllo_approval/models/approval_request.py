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
from odoo.exceptions import ValidationError


class ApprovalRequest(models.Model):
    _name = 'approval.request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Approval Request'

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        index=True,
        default=lambda self: 'New'
    )
    rule_id = fields.Many2one(
        'approval.rule',
        required=True,
        help="The approval rule that triggered this request."
    )
    line_id = fields.Many2one(
        'approval.rule.line',
        string='Approval Level',
        ondelete='set null',
        index=True,
        help="The level of the rule this request has to be approved at."
    )
    level = fields.Integer(
        string='Level',
        compute='_compute_level_info',
        store=True,
        help="Position of this request in the approval chain."
    )
    level_total = fields.Integer(
        string='Total Levels',
        compute='_compute_level_info',
        store=True,
        help="Number of levels the rule requires."
    )
    level_name = fields.Char(
        string='Level Name',
        compute='_compute_level_info',
        store=True,
        help="Readable position of this request, e.g. 'Level 2 of 3'."
    )
    approver_name = fields.Char(
        string='Approver Name',
        compute='_compute_approver_name',
        help="The user or group expected to answer this request."
    )
    company_id = fields.Many2one(
        related='rule_id.company_id',
        store=True,
        readonly=True,
        index=True
    )
    rule_type = fields.Selection(
        related='rule_id.rule_type',
        help="Type of rule (e.g., Condition, Always, etc.)"
    )
    res_model = fields.Char(
        required=True,
        help="The technical name of the model being approved."
    )
    res_id = fields.Integer(
        required=True,
        help="The ID of the record being approved."
    )
    res_name = fields.Char(
        string='Document',
        compute='_compute_res_name',
        help="Display name of the record being approved."
    )
    requested_by = fields.Many2one(
        'res.users',
        string='Requested By',
        help="The user who initiated the approval request."
    )
    approver_id = fields.Many2one(
        'res.users',
        help="The specific user assigned to approve this request."
    )
    approver_group_id = fields.Many2one(
        'res.groups',
        string='Approver Group',
        index=True,
        help="Any member of this group can answer this request."
    )
    state = fields.Selection(
        [
            ('pending', 'Pending'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
        ],
        default='pending',
        help="Current state of the approval request."
    )
    is_used = fields.Boolean(
        'Is Used',
        default=False,
        help="Flag to indicate if this request has already been processed."
    )
    note = fields.Text(
        'Note',
        help="Provide a reason for rejection or transfer."
    )
    can_approve = fields.Boolean(
        compute='_compute_can_approve',
        help="Technical field to check if the current user has permission to approve."
    )

    @api.depends('line_id', 'line_id.sequence', 'rule_id.approval_line_ids')
    def _compute_level_info(self):
        """Store where this request sits in its rule's approval chain."""
        for request in self:
            levels = request.rule_id._get_levels() if request.rule_id \
                else request.env['approval.rule.line']
            request.level_total = len(levels)
            if request.line_id and request.line_id in levels:
                request.level = list(levels).index(request.line_id) + 1
            else:
                request.level = 1
            if request.level_total > 1:
                request.level_name = _('Level %(level)s of %(total)s') % {
                    'level': request.level, 'total': request.level_total}
            else:
                request.level_name = _('Level %s') % request.level

    @api.depends('approver_id', 'approver_group_id')
    def _compute_approver_name(self):
        for request in self:
            request.approver_name = request.approver_id.display_name or \
                request.approver_group_id.display_name or False

    @api.depends('res_model', 'res_id')
    def _compute_res_name(self):
        for request in self:
            record = request._get_record()
            request.res_name = record.display_name if record else False

    def _compute_can_approve(self):
        """Check if the current user is the approver or in the approver group.

        Only the level answers for itself. The rule level fields are read as a
        fallback for requests raised before the levels existed, never for a
        request that already knows its level.
        """
        is_manager = self.env.user.has_group('cyllo_approval.group_approval_manager')
        for record in self:
            group = record.approver_group_id
            approver = record.approver_id
            if not record.line_id:
                group = group or record.rule_id.group_id
                approver = approver or record.rule_id.user_id
            is_approver = bool(approver) and approver == self.env.user
            in_group = bool(group) and group in self.env.user.groups_id
            record.can_approve = is_approver or in_group or is_manager

    def _get_record(self):
        """Return the record this request is about, if it still exists."""
        self.ensure_one()
        if not self.res_model or not self.res_id:
            return None
        if self.res_model not in self.env:
            return None
        record = self.env[self.res_model].sudo().browse(self.res_id)
        return record if record.exists() else None

    @api.model
    def _prepare_level_request(self, rule, line, res_model, res_id,
                               requested_by=None):
        """Values of the request asking ``line`` to approve the record.

        The approver comes from the level and from nowhere else. Falling back
        on the rule would hand the level to the approver of level one, since
        ``rule.user_id`` / ``rule.group_id`` mirror the first level.
        """
        return {
            'rule_id': rule.id,
            'line_id': line.id,
            'res_model': res_model,
            'res_id': res_id,
            'requested_by': (requested_by or self.env.user).id,
            'approver_id': line.user_id.id,
            'approver_group_id': line.group_id.id,
        }

    @api.model_create_multi
    def create(self, vals_list):
        """Create approval requests and update related records."""
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('approval.request') or 'New'
            if vals.get('line_id') and not (
                    vals.get('approver_id') or vals.get('approver_group_id')):
                line = self.env['approval.rule.line'].browse(vals['line_id'])
                vals['approver_id'] = line.user_id.id
                vals['approver_group_id'] = line.group_id.id
        requests = super().create(vals_list)

        template = self.env.ref(
            'cyllo_approval.mail_template_approval_request')
        for request in requests:
            if request.rule_id.is_email_request:
                template.send_mail(request.id, force_send=True)
            request._sync_document_state()
        return requests

    def _sync_document_state(self):
        """Point the document at this request so approvers see the buttons."""
        self.ensure_one()
        record = self._get_record()
        if record is None:
            return
        count = self.search_count([
            ('res_model', '=', self.res_model),
            ('res_id', '=', self.res_id),
        ])
        self._write_document_flags(record, {
            'x_approval_request_ids': [fields.Command.link(self.id)],
            'x_current_approver_id': self.approver_id.id,
            'x_current_group_id': self.approver_group_id.id,
            'x_approval_level_info': self._get_document_info(),
            'x_approval_request_count': count,
        })

    @api.model
    def _write_document_flags(self, record, values):
        """Write the approval flags the document actually carries.

        The flags are created on demand on the target model, so a document may
        legitimately be missing some of them until the rule is saved again.
        """
        values = {key: value for key, value in values.items()
                  if key in record._fields}
        if values:
            record.write(values)

    def _get_document_info(self):
        """Short sentence describing what the document is waiting for."""
        self.ensure_one()
        return _("%(rule)s - %(level)s - waiting for %(approver)s") % {
            'rule': self.rule_id.name,
            'level': self.level_name,
            'approver': self.approver_name or _('n/a'),
        }

    def _clear_document_state(self, record):
        """Unlink this request from the document and reset its approval flags."""
        self.ensure_one()
        if record is None:
            return
        self._write_document_flags(record, {
            'x_approval_request_ids': [fields.Command.unlink(self.id)],
            'x_is_state_approval': False,
            'x_current_approver_id': False,
            'x_current_group_id': False,
            'x_approval_level_info': False,
        })

    def action_approve(self):
        """Approve this level and hand the record over to the next one.

        When the approved level is the last one of the rule, the action the
        approval was requested for is replayed automatically, so the requester
        does not have to trigger it a second time.
        """
        self.ensure_one()
        if not self.can_approve:
            raise ValidationError("You do not have permission to approve this request.")
        self.write({'state': 'approved',
                    'is_used': True,
                    })
        record = self._get_record()
        self._clear_document_state(record)
        if self.rule_id.is_email_approve:
            template = self.env.ref(
                'cyllo_approval.mail_template_request_approved')
            template.send_mail(self.id, force_send=True)

        rule = self.rule_id.sudo()
        next_line = rule._get_next_level(self.line_id)
        if next_line:
            next_request = self.sudo().create(self._prepare_level_request(
                rule, next_line, self.res_model, self.res_id,
                requested_by=self.requested_by,
            ))
            body = _("Approved at %(level)s. Sent to %(approver)s for "
                     "%(next_level)s.") % {
                'level': self.level_name,
                'approver': next_request.approver_name or _('n/a'),
                'next_level': next_request.level_name,
            }
            self._message_log(body=body)
            if record is not None and hasattr(record, '_message_log'):
                record._message_log(body=body)
            return None

        if record is not None and hasattr(record, '_message_log'):
            record._message_log(body=_(
                "All approval levels of '%s' are approved.") % self.rule_id.name)
        if record is None:
            return None
        return rule._execute_after_approval(record, self)

    def action_reject(self):
        """Reject the request and stop the whole approval chain."""
        self.ensure_one()
        if not self.can_approve:
            raise ValidationError("You do not have permission to reject this request.")
        self.write({'state': 'rejected',
                    'is_used': True,
                    })

        record = self._get_record()
        self._clear_document_state(record)
        if record is not None and hasattr(record, '_message_log'):
            record._message_log(body=_(
                "Approval '%(rule)s' rejected at %(level)s by %(user)s.") % {
                'rule': self.rule_id.name,
                'level': self.level_name,
                'user': self.env.user.display_name,
            })
        if self.rule_id.is_email_reject:
            template = self.env.ref(
                'cyllo_approval.mail_template_request_rejected')
            template.send_mail(self.id, force_send=True)

    def action_transfer(self):
        """Open the transfer wizard for the approval request."""
        self.ensure_one()
        if not self.can_approve:
            raise ValidationError("You do not have permission to transfer this request.")

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'approval.transfer.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_request_id': self.id,
                'default_current_user_id': self.approver_id.id or self.env.uid,
            },
        }

    def action_open_related_record(self):
        """Open the source document from the approval request."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": self.res_model,
            "view_mode": "form",
            "res_id": self.res_id,
            "target": "current",
        }
