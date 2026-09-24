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
from lxml import etree
from odoo import _, api, models
from odoo.exceptions import ValidationError


class BaseModel(models.AbstractModel):
    _inherit = 'base'

    def _get_pending_approval_request(self):
        """Return the approval request currently waiting on this record."""
        self.ensure_one()
        requests = self.sudo().x_approval_request_ids.filtered(
            lambda request: request.state == 'pending')
        if not requests:
            raise ValidationError(
                _("There is no pending approval request on this record."))
        return requests.sorted('id')[0]

    def _get_approval_request_for_action(self):
        """Return the pending request, making sure the user may answer it."""
        self.ensure_one()
        request = self._get_pending_approval_request()
        if not request.can_approve:
            raise ValidationError(
                _("You are not allowed to answer %s of this approval.")
                % request.level_name)
        return request

    def action_dynamic_approve(self):
        """Called when clicking the dynamically injected Approve button."""
        self.ensure_one()
        request = self._get_approval_request_for_action()
        level_name = request.level_name
        result = request.sudo().action_approve()
        if hasattr(self, '_message_log'):
            self._message_log(body=_("%s approved.") % level_name)
        return result

    def action_dynamic_reject(self):
        """Called when clicking the dynamically injected Reject button."""
        self.ensure_one()
        request = self._get_approval_request_for_action()
        level_name = request.level_name
        request.sudo().action_reject()
        if hasattr(self, '_message_log'):
            self._message_log(body=_("%s rejected.") % level_name)

    def action_dynamic_transfer(self):
        """Called when clicking the dynamically injected Transfer button."""
        self.ensure_one()
        request = self._get_approval_request_for_action()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'approval.transfer.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_request_id': request.id,
                'default_current_user_id': self.env.uid,
            },
        }

    def action_request_approval(self):
        """Open the wizard asking the next level of the applicable state rule."""
        self.ensure_one()
        approval_rule = self.env['approval.rule'].sudo()
        rules = approval_rule.search([
            ('model_name', '=', self._name),
            ('rule_type', '=', 'state'),
            '|', ('company_id', '=', False), ('company_id', 'in', self.env.companies.ids)
        ]).sorted(lambda rule: rule.sequence)
        if not rules:
            return None
        for rule in rules:
            if not rule._match_record(self):
                continue
            action = rule._check_record_approval(self)
            if action:
                return action
        return None

    def action_open_approval_requests(self):
        """Open all approval requests related to the document."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Approval Requests",
            "res_model": "approval.request",
            "view_mode": "tree,form",
            "domain": [
                ("res_model", "=", self._name),
                ("res_id", "=", self.id)
            ],
            "target": "current",
        }

    @api.model
    def _approval_request_count(self):
        """Compute count for stat button."""
        approval_request = self.env["approval.request"]
        for rec in self:
            rec.x_approval_request_count = approval_request.search_count([
                ("res_model", "=", rec._name),
                ("res_id", "=", rec.id)
            ])

    @api.model
    def _get_approval_approver_condition(self, rules):
        """Build the domain-like condition matching the current approver.

        ``x_current_group_id`` alone cannot tell the client whether the user
        belongs to that group, so the groups the user is actually a member of
        are resolved here, server side, while rendering the view.
        """
        group_ids = set()
        for rule in rules:
            group_ids |= rule._get_approver_group_ids(self.env.user)
        condition = "x_current_approver_id == uid"
        if group_ids:
            condition = "(%s or x_current_group_id in %s)" % (
                condition, sorted(group_ids))
        return condition

    @api.model
    def get_view(self, view_id=None, view_type='form', **options):
        res = super().get_view(view_id=view_id, view_type=view_type, **options)
        if view_type != 'form':
            return res
        user = self.env.user
        model_name = res.get('model')
        approval_rule = self.env['approval.rule'].sudo()
        rules = approval_rule.search(
            [('model_name', '=', model_name),
             '|', ('company_id', '=', False), ('company_id', 'in', self.env.companies.ids)],
            order='sequence asc',
        )
        if not rules:
            return res
        ordered_rules = rules.sorted(key=lambda r: r.sequence)
        active_rule = next(
            (rule for rule in ordered_rules if rule._is_user_approver(user)),
            None
        )
        approver_condition = self._get_approval_approver_condition(
            ordered_rules)
        approval_invisible = "not (x_approval_request_ids and %s)" % \
            approver_condition
        arch = etree.fromstring(res['arch'])

        def ensure_hidden_field(field_name):
            if not arch.xpath(f'//field[@name="{field_name}"]'):
                sheet_nodes = arch.xpath('//sheet')
                if sheet_nodes:
                    field = etree.Element('field', {
                        'name': field_name,
                        'invisible': '1'
                    })
                    sheet_nodes[0].insert(0, field)
        ensure_hidden_field("x_approval_request_ids")
        ensure_hidden_field("x_is_state_approval")
        ensure_hidden_field("x_approval_comment")
        ensure_hidden_field("x_current_approver_id")
        ensure_hidden_field("x_current_group_id")
        ensure_hidden_field("x_approval_request_count")
        sheet_nodes = arch.xpath('//sheet')
        if sheet_nodes:
            sheet = sheet_nodes[0]
            warning_div = etree.Element(
                'div',
                {
                    'class': 'alert alert-warning o_form_label',
                    'role': 'alert',
                    'invisible': "not x_is_state_approval or "
                                 "x_approval_request_ids"
                }
            )
            warning_div.text = "Approval is required before changing the state. Please request approval."
            sheet.insert(0, warning_div)
            if 'x_approval_level_info' in self._fields:
                pending_div = etree.Element(
                    'div',
                    {
                        'class': 'alert alert-info o_form_label',
                        'role': 'alert',
                        'invisible': "not x_approval_request_ids",
                    }
                )
                pending_div.text = "Waiting for approval: "
                pending_div.append(etree.Element('field', {
                    'name': 'x_approval_level_info',
                    'nolabel': '1',
                    'readonly': '1',
                    'class': 'oe_inline',
                }))
                sheet.insert(1, pending_div)
            if active_rule and active_rule.is_comment:
                comment_group = etree.Element(
                    "group",
                    {
                        "string": "Approval Comment",
                        "invisible": "not x_approval_request_ids"
                    }
                )
                comment_field = etree.Element("field", {
                    "name": "x_approval_comment",
                    "placeholder": "Enter your private approval comment"
                })
                comment_group.append(comment_field)
                sheet.append(comment_group)
        headers = arch.xpath('//header')
        if headers:
            header = headers[0]
            approve_btn = etree.Element('button', {
                'name': 'action_dynamic_approve',
                'string': 'Approve',
                'type': 'object',
                'class': 'oe_highlight cyllo_approval_btn',
                'invisible': approval_invisible,
            })
            reject_btn = etree.Element('button', {
                'name': 'action_dynamic_reject',
                'string': 'Reject',
                'type': 'object',
                'class': 'btn-secondary cyllo_approval_btn',
                'invisible': approval_invisible,
            })
            transfer_btn = etree.Element('button', {
                'name': 'action_dynamic_transfer',
                'string': 'Transfer',
                'type': 'object',
                'class': 'btn-info cyllo_approval_btn',
                'invisible': approval_invisible,
            })
            request_btn = etree.Element('button', {
                'name': 'action_request_approval',
                'string': 'Request Approval',
                'type': 'object',
                'class': 'btn-secondary',
                'invisible': "not x_is_state_approval or x_approval_request_ids"
            })
            stat_btn = etree.Element("button", {
                "name": "action_open_approval_requests",
                "type": "object",
                "class": "oe_stat_button",
                "icon": "fa-check-square",
                "invisible": "x_approval_request_count == 0",
            })
            field_count = etree.Element("field", {
                "name": "x_approval_request_count",
                "widget": "statinfo"
            })
            stat_btn.append(field_count)
            header.append(approve_btn)
            header.append(reject_btn)
            header.append(request_btn)
            header.append(transfer_btn)

            # Place stat_btn in button_box, not header
            button_box_nodes = arch.xpath('//div[@class="oe_button_box"] | //div[@name="button_box"]')
            if button_box_nodes:
                button_box = button_box_nodes[0]
                button_box.append(stat_btn)
            elif sheet_nodes:
                button_box = etree.Element('div', {'class': 'oe_button_box', 'name': 'button_box'})
                button_box.append(stat_btn)
                # insert button_box as the first child of sheet, or after ribbon if any.
                # Just inserting at 0 is fine, or right after header/web_ribbon
                sheet.insert(0, button_box)

        if active_rule and active_rule.rule_type == "button":
            button_nodes = arch.xpath(
                f".//button[@name='{active_rule.button_id.name}']")
            if button_nodes:
                target_conditions = []
                for btn in button_nodes:
                    inv = btn.get("invisible")
                    if inv:
                        target_conditions.append(f"({inv})")
                if target_conditions:
                    combined_invisible = " and ".join(target_conditions)
                    approval_buttons = arch.xpath(
                        ".//button[contains(@class,'cyllo_approval_btn')]"
                    )
                    for btn in approval_buttons:
                        own_inv = btn.get("invisible")
                        if own_inv:
                            final = f"({own_inv}) or ({combined_invisible})"
                        else:
                            final = combined_invisible
                        btn.set("invisible", final)
        res['arch'] = etree.tostring(arch, encoding='unicode')
        return res
