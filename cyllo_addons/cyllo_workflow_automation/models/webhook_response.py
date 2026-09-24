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
"""
Generic Webhook Response Action Processor
==========================================
Processes the JSON response returned by any webhook / API call and executes
zero or more configurable post-response actions without any hardcoded
platform-specific logic.

Each action is a dict with the following schema
(all fields optional unless marked *required*):

    {
        "extract_path": "data.payment_url",   # *required* — dot-separated key path
        "action_type": "chatter_link",        # *required* — see ACTION_TYPES below
        "field_to_write": "payment_url",      # for action_type="write_field"
        "email_template_id": 42,              # for action_type="send_email"
        "variable_name": "payment_url",       # for action_type="store_variable"
        "label": "Pay Now",                   # human label used in chatter messages
    }

Supported action_type values
------------------------------
chatter_link      — Post the extracted URL as a clickable link in the record chatter
chatter_message   — Post the raw value as a plain text message in the chatter
write_field       — Write the extracted value onto a field of the trigger record
send_email        — Send an email notification containing the extracted value
redirect_url      — Return a client-side redirect action (browser redirect)
store_variable    — Store the value into the workflow execution context dict
log_info          — Log the value at INFO level (useful for debugging)
"""

import logging

from odoo import _, api, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# ── Supported action type identifiers ──────────────────────────────────────────
ACTION_TYPES = {
    'chatter_link',
    'chatter_message',
    'write_field',
    'send_email',
    'redirect_url',
    'store_variable',
    'log_info',
}


def _extract_value(response_data, path):
    """
    Traverse a nested dict/list using a dot-separated key path, e.g. 'links.0.href'.
    Returns None if any segment of the path is missing.
    """
    if not path or path == '.':
        return response_data
    if not isinstance(response_data, (dict, list)):
        return None
    parts = path.split('.')
    current = response_data
    for part in parts:
        if current is None:
            return None
        if isinstance(current, dict):
            current = current.get(part)
        elif isinstance(current, list):
            try:
                current = current[int(part)]
            except (ValueError, IndexError):
                return None
        else:
            return None
    return current


class WebhookResponseProcessor(models.AbstractModel):
    """
    Abstract mixin that provides generic webhook response action processing via
    process_response_actions(), called from generated workflow Python code.
    """

    _name = 'webhook.response.processor'
    _description = 'Generic Webhook Response Action Processor'

    @api.model
    def process_response_actions(self, response_data, actions, record=None, context_vars=None):
        """
        Execute all configured response actions for a single webhook call against `response_data`.
        Returns a client-side redirect action dict if a 'redirect_url' action fired, else None.
        """
        if not actions or not isinstance(actions, list):
            return None

        if not isinstance(response_data, (dict, list)):
            _logger.warning(
                "WebhookResponseProcessor: response_data is not a dict/list (%s) — "
                "skipping action processing.",
                type(response_data).__name__,
            )
            return None

        client_action = None

        for action_cfg in actions:
            if not isinstance(action_cfg, dict):
                continue

            action_type = (action_cfg.get('action_type') or '').strip()
            extract_path = (action_cfg.get('extract_path') or '').strip()
            label = (action_cfg.get('label') or extract_path or 'value').strip()

            if not action_type or action_type not in ACTION_TYPES:
                _logger.warning(
                    "WebhookResponseProcessor: unknown action_type %r — skipping.", action_type
                )
                continue

            # ── Extract value from response ────────────────────────────────────
            extracted = _extract_value(response_data, extract_path) if extract_path else response_data
            if extracted is None:
                _logger.info(
                    "WebhookResponseProcessor: path %r returned None in response — skipping action %r.",
                    extract_path, action_type,
                )
                continue

            value_str = str(extracted)

            try:
                result = self._dispatch_action(
                    action_type=action_type,
                    value=extracted,
                    value_str=value_str,
                    label=label,
                    action_cfg=action_cfg,
                    record=record,
                    context_vars=context_vars,
                )
                if result and isinstance(result, dict) and result.get('type'):
                    client_action = result
            except Exception as exc:
                _logger.error(
                    "WebhookResponseProcessor: action %r on path %r failed: %s",
                    action_type, extract_path, exc,
                )
                # Non-fatal: continue processing remaining actions

        return client_action

    @api.model
    def _dispatch_action(self, action_type, value, value_str, label, action_cfg,
                         record=None, context_vars=None):
        """Route to the specific action handler."""

        if action_type == 'log_info':
            _logger.info(
                "WebhookResponseProcessor [log_info] %s = %r", label, value
            )
            return None

        if action_type == 'store_variable':
            var_name = (action_cfg.get('variable_name') or '').strip()
            if var_name and isinstance(context_vars, dict):
                context_vars[var_name] = value
                _logger.info(
                    "WebhookResponseProcessor [store_variable] stored %r = %r",
                    var_name, value,
                )
            return None

        if action_type == 'redirect_url':
            url = value_str
            _logger.info("WebhookResponseProcessor [redirect_url] %s", url)
            return {
                'type': 'ir.actions.act_url',
                'url': url,
                'target': action_cfg.get('target', 'new'),
            }

        # ── Actions that need a valid record ──────────────────────────────────
        if record is None or not hasattr(record, '_name'):
            _logger.warning(
                "WebhookResponseProcessor: action %r requires a record but none was provided.",
                action_type,
            )
            return None

        if hasattr(record, '__len__') and len(record) == 0:
            _logger.warning(
                "WebhookResponseProcessor: action %r got an empty recordset — skipping.",
                action_type,
            )
            return None

        rec = record[:1] if hasattr(record, '__len__') and len(record) > 1 else record

        if action_type == 'chatter_link':
            return self._action_chatter_link(rec, value_str, label, action_cfg)

        if action_type == 'chatter_message':
            return self._action_chatter_message(rec, value_str, label, action_cfg)

        if action_type == 'write_field':
            return self._action_write_field(rec, value, value_str, action_cfg)

        if action_type == 'send_email':
            return self._action_send_email(rec, value_str, label, action_cfg)

        return None

    # ── Individual action handlers ────────────────────────────────────────────

    @api.model
    def _action_chatter_link(self, record, url, label, action_cfg):
        """Post a clickable URL link in the record's chatter."""
        if not hasattr(record, 'message_post'):
            _logger.warning(
                "WebhookResponseProcessor [chatter_link]: model %s has no message_post.",
                record._name,
            )
            return None
        from markupsafe import Markup
        body = Markup(
            '<p><strong>%s:</strong> '
            '<a href="%s" target="_blank">%s</a></p>'
        ) % (label, url, url)
        record.message_post(body=body, message_type='comment', subtype_xmlid='mail.mt_note')
        _logger.info(
            "WebhookResponseProcessor [chatter_link] posted link on %s #%s",
            record._name, record.id,
        )
        return None

    @api.model
    def _action_chatter_message(self, record, value_str, label, action_cfg):
        """Post a plain-text message in the record's chatter."""
        if not hasattr(record, 'message_post'):
            return None
        from markupsafe import Markup
        body = Markup('<p><strong>%s:</strong> %s</p>') % (label, value_str)
        record.message_post(body=body, message_type='comment', subtype_xmlid='mail.mt_note')
        _logger.info(
            "WebhookResponseProcessor [chatter_message] posted on %s #%s",
            record._name, record.id,
        )
        return None

    @api.model
    def _action_write_field(self, record, value, value_str, action_cfg):
        """Write the extracted value onto a specific field of the trigger record."""
        field_name = (action_cfg.get('field_to_write') or '').strip()
        if not field_name:
            _logger.warning(
                "WebhookResponseProcessor [write_field]: field_to_write not specified — skipping."
            )
            return None

        # Resolve field type to coerce value appropriately
        model_fields = record._fields
        if field_name not in model_fields:
            _logger.warning(
                "WebhookResponseProcessor [write_field]: field %r not found on model %s — skipping.",
                field_name, record._name,
            )
            return None

        field_obj = model_fields[field_name]
        write_val = value_str  # default: string

        if field_obj.type in ('integer',):
            try:
                write_val = int(value)
            except (ValueError, TypeError):
                write_val = value_str
        elif field_obj.type in ('float', 'monetary'):
            try:
                write_val = float(value)
            except (ValueError, TypeError):
                write_val = value_str
        elif field_obj.type == 'boolean':
            write_val = bool(value)

        try:
            record.write({field_name: write_val})
            _logger.info(
                "WebhookResponseProcessor [write_field] wrote %r = %r on %s #%s",
                field_name, write_val, record._name, record.id,
            )
        except Exception as exc:
            _logger.error(
                "WebhookResponseProcessor [write_field] failed to write %r on %s #%s: %s",
                field_name, record._name, record.id, exc,
            )
        return None

    @api.model
    def _action_send_email(self, record, value_str, label, action_cfg):
        """
        Send an email via the configured template if `email_template_id` is set, otherwise
        compose a generic notification to the record's partner email or configured recipients.
        """
        template_id = action_cfg.get('email_template_id')
        recipients = action_cfg.get('email_recipients', '')

        if template_id:
            template = self.env['mail.template'].sudo().browse(int(template_id))
            if template.exists():
                template.with_context(webhook_value=value_str).send_mail(
                    record.id, force_send=True
                )
                _logger.info(
                    "WebhookResponseProcessor [send_email] sent template #%s for %s #%s",
                    template_id, record._name, record.id,
                )
                return None

        # Fallback: compose a simple notification email
        partner_email = getattr(getattr(record, 'partner_id', None), 'email', None)
        to_email = recipients or partner_email
        if not to_email:
            _logger.warning(
                "WebhookResponseProcessor [send_email]: no recipient email found — skipping."
            )
            return None

        subject = _("Webhook Response: %s") % label
        from markupsafe import Markup
        body_html = Markup(
            '<p>A webhook response was received.</p>'
            '<p><strong>%s:</strong> %s</p>'
        ) % (label, value_str)

        try:
            mail = self.env['mail.mail'].sudo().create({
                'subject': subject,
                'body_html': body_html,
                'email_to': to_email,
                'auto_delete': True,
            })
            mail.send()
            _logger.info(
                "WebhookResponseProcessor [send_email] sent to %s for %s #%s",
                to_email, record._name, record.id,
            )
        except Exception as exc:
            _logger.error(
                "WebhookResponseProcessor [send_email] failed: %s", exc
            )
        return None
