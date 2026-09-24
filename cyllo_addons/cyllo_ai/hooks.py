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
import logging

_logger = logging.getLogger(__name__)


def seed_config(env):
    """Carry over any pre-app ``ir.config_parameter`` values as the first config.

    Reads the legacy configuration (how the old ``res.config.settings`` fields
    stored it) and, only if no ``cyllo.ai.config`` record exists yet, creates
    one from it and marks it active. Idempotent and safe to run on install or
    upgrade — a database that already has configs is left alone.
    """
    config = env['cyllo.ai.config'].sudo()
    if config.search_count([]):
        return None  # configs already exist — nothing to migrate into

    param = env['ir.config_parameter'].sudo()
    provider = param.get_param('cyllo_agent.llm') or False
    api_key = param.get_param('cyllo_agent.api_key') or False
    if not (provider or api_key):
        return None  # no legacy values to migrate

    vals = {
        'name': 'Migrated Configuration',
        'is_active': True,
        'provider': provider,
        'api_key': api_key,
        'openrouter_model': param.get_param('openrouter.model') or False,
    }
    model_id = param.get_param('agent.llm_model_id')
    if model_id:
        try:
            llm = env['cyllo.llm'].browse(int(model_id))
            if llm.exists():
                vals['llm_model_id'] = llm.id
        except (ValueError, TypeError):
            _logger.warning('cyllo_ai: could not migrate agent.llm_model_id=%r',
                            model_id)
    record = config.create(vals)
    _logger.info('cyllo_ai: seeded cyllo.ai.config from legacy parameters')
    return record


def post_init_hook(env):
    """Migrate legacy ``ir.config_parameter`` values into a config on install."""
    seed_config(env)
