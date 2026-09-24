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
from odoo import _, api, models
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval


class IrActionsServer(models.Model):
    _inherit = "ir.actions.server"

    def _get_active_record(self):
        """Return active record(s) from context if available."""
        active_model = self._context.get("active_model")
        active_ids = self._context.get("active_ids", [])
        if active_model and active_ids:
            return self.env[active_model].browse(active_ids)
        return None

    def _get_server_rules(self):
        """Fetch approval rules for this server action."""
        rules = self.env["approval.rule"].sudo().search([
            ("rule_type", "=", "server"),
            ("server_action_id", "=", self.id),
            '|', ('company_id', '=', False), ('company_id', 'in', self.env.companies.ids)
        ])
        bypass = self.env.context.get('approval_bypass_rule_ids') or []
        return rules.filtered(lambda rule: rule.id not in bypass)

    def _parse_rule_domain(self, rule):
        """Parse domain text into Python list safely."""
        if not rule.domain:
            return []
        try:
            return safe_eval(rule.domain)
        except Exception:
            raise UserError(_(
                "Invalid domain in approval rule '%s': %s"
            ) % (rule.name, rule.domain))

    def _get_matched_rules(self, rules, active_record):
        """Return only the rules where domain is satisfied."""
        matched = []
        for rule in rules:
            domain = self._parse_rule_domain(rule)
            if not domain:
                matched.append(rule)
                continue
            if active_record and active_record.filtered_domain(domain):
                matched.append(rule)
        return matched

    def _check_existing_approval(self, rule, active_model, active_ids):
        """Return the wizard action when a record still needs an approval.

        Every level of the rule has to be approved before the server action is
        allowed to run; the next level is requested automatically as soon as
        the previous one answers.
        """
        records = self.env[active_model].browse(active_ids)
        for record in records:
            action = rule._check_record_approval(record)
            if action:
                return action
        return None

    @api.model
    def run(self):
        """
        Override: apply approval rules before server action executes.
        """
        active_record = self._get_active_record()
        active_model = self._context.get("active_model")
        active_ids = self._context.get("active_ids", [])
        rules = self._get_server_rules()
        if not rules:
            return super(IrActionsServer, self).run()
        matched_rules = self._get_matched_rules(rules, active_record)
        if not matched_rules:
            return super(IrActionsServer, self).run()
        for rule in matched_rules:
            action = self._check_existing_approval(rule, active_model, active_ids)
            if action:
                return action
        return super(IrActionsServer, self).run()
