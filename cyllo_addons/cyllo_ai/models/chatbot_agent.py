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
Chatbot agent entry point (thin).

This AbstractModel is the Odoo-idiomatic boundary the controller calls into
(``request.env['chatbot.agent']``). It does no heavy lifting — it delegates to
the framework-free engine in ``core/``, passing ``self.env`` in.
"""
from odoo import models

from odoo.addons.cyllo_ai.core.orchestrator import Orchestrator
from odoo.addons.cyllo_ai.core.profiles import resolve_profile
from odoo.addons.cyllo_ai.core.tools.builtins import (
    DEFAULT_TOOL_CLASSES,
    build_registry_from,
)


class ChatbotAgent(models.AbstractModel):
    _name = "chatbot.agent"
    _description = "Chatbot Agent"

    # -- tool seam ----------------------------------------------------------
    # These two methods are the extension point: another module inherits
    # chatbot.agent and overrides _ai_tool_classes to contribute tools, without
    # editing cyllo_ai. Example:
    #
    #     def _ai_tool_classes(self, profile):
    #         return super()._ai_tool_classes(profile) + [RecommendChartTool]

    def _ai_tool_classes(self, profile):
        """Return the Tool classes available for ``profile`` (a list).

        Base = the built-in belt. Override to append module tools. ``profile``
        is passed so contributions can be scoped per profile later.
        """
        return list(DEFAULT_TOOL_CLASSES)

    def _ai_build_registry(self, profile):
        """Assemble the per-turn ToolRegistry from :meth:`_ai_tool_classes`."""
        return build_registry_from(self._ai_tool_classes(profile))

    def _orchestrator(self, ui_context=None):
        """Build an Orchestrator for this turn — profile resolved
        deterministically from the (untrusted) client ui_context hint."""
        profile = resolve_profile(self.env, ui_context)
        registry = self._ai_build_registry(profile)
        return Orchestrator(self.env, profile=profile, ui_context=ui_context,
                            registry=registry)

    def process_query(self, text, session_id, company_ids=None, interrupted=False,
                      ui_context=None):
        """Process one user turn. Returns ``{response, last_message}``."""
        return self._orchestrator(ui_context).run(
            text, session_id, company_ids=company_ids, interrupted=interrupted
        )

    def process_query_stream(self, text, session_id, company_ids=None, interrupted=False,
                             ui_context=None):
        """Stream one user turn as typed events (generator). See Orchestrator.run_stream."""
        yield from self._orchestrator(ui_context).run_stream(
            text, session_id, company_ids=company_ids, interrupted=interrupted
        )
