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
Contribute analytics tools to the Cyllo AI assistant via its tool seam.

Inheriting ``chatbot.agent`` and overriding ``_ai_tool_classes`` is the entire
integration — no changes to cyllo_ai are required.
"""
from odoo import models

from odoo.addons.cyllo_ai_analytics.core.tools import (
    RecommendChartTool,
    SuggestSheetChartsTool,
    EditCurrentChartTool,
    OpenQuickDashboardTool,
    EditQuickDashboardTool,
    EditLiveDashboardTool,
)


class ChatbotAgent(models.AbstractModel):
    _inherit = "chatbot.agent"

    def _ai_tool_classes(self, profile):
        """Append the analytics tools to the assistant's belt."""
        return super()._ai_tool_classes(profile) + [
            RecommendChartTool,
            SuggestSheetChartsTool,
            EditCurrentChartTool,
            OpenQuickDashboardTool,
            EditQuickDashboardTool,
            EditLiveDashboardTool,
        ]
