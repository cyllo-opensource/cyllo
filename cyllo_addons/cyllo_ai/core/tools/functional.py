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
Functional-assistant tools — Tier-1 introspection of the ERP itself.

"How do I / where is / can Cyllo do X" questions are answered by reading
the live install (menus the user can see, Settings fields, data models),
never from the model's training-data memory of generic Odoo — paths and
setting names returned here exist in THIS install by construction.

All three are read-only and registered in every profile.
"""
from .base import Tool, ToolContext


class DescribeFeatureTool(Tool):
    name = "describe_feature"
    label = "Looking up feature"
    description = (
        "FIRST CHOICE for functionality/navigation questions: 'how do I X', "
        "'where is X', 'how to enable X', 'does Cyllo have X'. Searches this "
        "Cyllo install's menus (only those the user can see), Settings toggles "
        "and data models in one call, returning exact menu paths with links. "
        "Base your answer ONLY on what it returns — never invent menu paths or "
        "setting names. Not for data questions (use search_records etc.)."
    )
    is_read_only = True
    input_schema = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Feature keywords, e.g. 'multi currency', "
                               "'tax configuration', 'discount sale order'.",
            },
        },
        "required": ["query"],
    }

    def run(self, ctx: ToolContext, query):
        return ctx.env['chatbot.tools'].describe_feature(query)


class FindMenuTool(Tool):
    name = "find_menu"
    label = "Finding menu"
    description = (
        "Find menus in this Cyllo install matching keywords; returns exact menu "
        "paths (e.g. 'Accounting / Configuration / Taxes') with action links, "
        "limited to menus the current user can actually see. Use to refine after "
        "describe_feature, or when the user asks where a specific screen lives."
    )
    is_read_only = True
    input_schema = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Menu keywords, e.g. 'payment terms'.",
            },
        },
        "required": ["query"],
    }

    def run(self, ctx: ToolContext, query):
        return ctx.env['chatbot.tools'].find_menu(query)


class FindSettingTool(Tool):
    name = "find_setting"
    label = "Finding setting"
    description = (
        "Search the Settings screen of this Cyllo install by keywords; returns "
        "matching setting labels with their help text and a link to Settings. "
        "Use for 'how to enable/activate/turn on X' questions."
    )
    is_read_only = True
    input_schema = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Setting keywords, e.g. 'multi currency'.",
            },
        },
        "required": ["query"],
    }

    def run(self, ctx: ToolContext, query):
        return ctx.env['chatbot.tools'].find_setting(query)
