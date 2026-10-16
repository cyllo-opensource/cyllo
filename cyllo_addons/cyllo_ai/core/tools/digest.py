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
"""Activity digest tool — "what happened this week / month / in a period"."""
from .base import Tool, ToolContext


class ActivityDigestTool(Tool):
    name = "activity_digest"
    label = "Summarizing activity"
    description = (
        "FIRST CHOICE for overview questions about a period across the business: "
        "'what happened this week', 'summary of this month', 'what did we do "
        "today / last week / last quarter / between X and Y'. Returns counts, "
        "totals and links per installed app (sales, invoicing, purchase, CRM, "
        "inventory, manufacturing, project, helpdesk, HR, activities) plus the "
        "previous period's counts. Resolve the period from the user's words "
        "using today from the context: 'this week' = Monday to today, 'this "
        "month' = the 1st to today, a custom range as given. Follow the "
        "result's answer_style."
    )
    is_read_only = True
    input_schema = {
        "type": "object",
        "properties": {
            "date_from": {"type": "string", "description": "First day, YYYY-MM-DD."},
            "date_to": {"type": "string", "description": "Last day, YYYY-MM-DD."},
        },
        "required": ["date_from", "date_to"],
    }

    def run(self, ctx: ToolContext, date_from, date_to):
        return ctx.env['cyllo.ai.digest'].get_digest(date_from, date_to, ctx.company_ids)
