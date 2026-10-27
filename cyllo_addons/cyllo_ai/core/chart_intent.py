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
import logging

from .llm_client import LLMClient

_logger = logging.getLogger(__name__)

CHART_INTENT_PROMPT = """You check one rule for a business assistant's chat.

Rule: a chart is drawn in the answer only when the user explicitly asks for a \
visual: a chart, graph, plot or visualization, or a chart type such as bar, line \
or pie, in any wording or language. Asking for figures, a list, a table or a \
breakdown is not asking for a chart; those are answered as text or a table, with \
a "View as chart" button the user can press.

User message:
\"\"\"{message}\"\"\"

Does this message explicitly ask for a chart? Reply with only YES or NO."""

CHART_REQUEST_HINT = (
    "CHART REQUESTED: the user's latest message explicitly asks for a chart. Get "
    "the figures, or reuse the ones already given in this conversation, and call "
    "`render_chart` (or `recommend_chart`) with them, even when there is only one "
    "value. Do not answer that a chart cannot be shown, and do not ask what to "
    "chart when the figures are already in the conversation."
)


def user_asked_for_chart(ctx):
    """True when the LLM judges that the user's message explicitly asks for a
    chart; the answer is kept on ``ctx`` so a turn asks only once."""
    cached = getattr(ctx, '_user_asked_for_chart', None)
    if cached is not None:
        return cached
    message = (ctx.user_query or '').strip()
    asked = False
    if message:
        try:
            answer = LLMClient(ctx.env).complete(
                CHART_INTENT_PROMPT.format(message=message[:2000]), timeout=20)
            asked = (answer or '').strip().upper().startswith('YES')
        except Exception as error:
            _logger.warning("[cyllo_ai] chart intent check failed: %s", error)
    ctx._user_asked_for_chart = asked
    return asked
