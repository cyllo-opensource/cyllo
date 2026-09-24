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
Cyllo AI — framework-free engine (core).

Plain-Python package (not Odoo models). Engine components receive an Odoo
``env`` when they need database access, which keeps the framework-agnostic
logic (LLM client, context assembly, normalization, the agent loop) decoupled
and unit-testable.

Entry point for the rest of the addon:

    from odoo.addons.cyllo_ai.core.orchestrator import Orchestrator
    Orchestrator(env).run(text, session_id, company_ids)
"""
