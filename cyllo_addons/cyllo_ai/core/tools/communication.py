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
"""
Communication tools — send email / SMS with a mandatory preview-confirm step.

Calling these does NOT send anything: the implementation drafts the message
and pauses the turn (the same ``__interrupt__`` sandbox as risky CRUD), the
user sees a full preview in chat, and only an explicit "proceed" sends it.
"""
from .base import Tool, ToolContext


class SendEmailTool(Tool):
    name = "send_email"
    label = "Drafting email"
    description = (
        "Send an email to a partner/customer. Compose the email yourself from "
        "the user's request (short specific subject, professional plain-text "
        "body); the tool shows the user a preview and asks for confirmation "
        "automatically — call it directly, never ask permission first and "
        "NEVER send emails via write_records."
    )
    is_read_only = False
    input_schema = {
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "The email body, plain text with line breaks "
                               "(greeting / content / sign-off).",
            },
            "partner_id": {
                "type": "integer",
                "description": "Recipient partner id (preferred when known, "
                               "e.g. from the user's message).",
            },
            "partner": {
                "type": "string",
                "description": "Recipient name, used when no partner_id is known.",
            },
            "subject": {
                "type": "string",
                "description": "Email subject — short and specific.",
            },
        },
        "required": ["message"],
    }

    def run(self, ctx: ToolContext, message, partner_id=None, partner=None, subject=None):
        return ctx.env['chatbot.tools'].prepare_email(
            message, partner_id=partner_id, partner=partner, subject=subject)


class SendTextTool(Tool):
    name = "send_text"
    label = "Drafting SMS"
    description = (
        "Send a text message (SMS) to a partner/customer through the configured "
        "SMS gateway. Keep the text short (SMS-length); the tool previews and "
        "asks the user for confirmation automatically — call it directly. "
        "NEVER send SMS via write_records."
    )
    is_read_only = False
    input_schema = {
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "The SMS text to send.",
            },
            "partner_id": {
                "type": "integer",
                "description": "Recipient partner id (preferred when known).",
            },
            "partner": {
                "type": "string",
                "description": "Recipient name, used when no partner_id is known.",
            },
        },
        "required": ["message"],
    }

    def run(self, ctx: ToolContext, message, partner_id=None, partner=None):
        return ctx.env['chatbot.tools'].prepare_text_message(
            message, partner_id=partner_id, partner=partner)


class SendInternalMessageTool(Tool):
    name = "send_internal_message"
    label = "Drafting message"
    description = (
        "Send an internal message to another Cyllo user (a colleague) as a "
        "Discuss direct message. Compose the message yourself from the user's "
        "request; the tool shows a preview and asks for confirmation "
        "automatically — call it directly, never ask permission first and "
        "NEVER send internal messages via write_records."
    )
    is_read_only = False
    input_schema = {
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "The message text to send.",
            },
            "user_id": {
                "type": "integer",
                "description": "Recipient user id (preferred when known).",
            },
            "user": {
                "type": "string",
                "description": "Recipient user name, used when no user_id is known.",
            },
        },
        "required": ["message"],
    }

    def run(self, ctx: ToolContext, message, user_id=None, user=None):
        return ctx.env['chatbot.tools'].prepare_internal_message(
            message, user_id=user_id, user=user)
