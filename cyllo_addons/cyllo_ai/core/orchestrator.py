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
Orchestrator — the agent loop.

A single agent with native function-calling. One ``run()`` does:

    load session  →  (resume pending write?)  →  append user turn
                  →  ReAct loop:
                        assemble [system + context + windowed history]
                        → normalize → LLM(with tools)
                        → if tool_calls: execute (read-only inline; risky
                          writes pause for confirmation) and loop
                        → else: final answer
                  →  persist  →  return {response, last_message}

Write safety (sandbox): when ``write_records`` reports a data-modifying action,
the loop pauses, stores the pending operation on the session, and returns a
confirmation prompt in ``response``. The UI re-calls with ``interrupted=True``
and the user's decision ("proceed" to run it).

Agent profiles (core/profiles.py) select the system prompt + tool belt per
turn — deterministically, from ui_context. Seams still stubbed: context
``diff()``, cap-and-spill.
"""
import json
import logging
import time

from odoo.exceptions import UserError

from .context.fragments import (
    ChartContextFragment,
    CompanyContextFragment,
    DateContextFragment,
    LiveDashboardContextFragment,
    MentionContextFragment,
    QuickDashboardContextFragment,
    UIContextFragment,
    UserContextFragment,
)
from .llm_client import LLMClient
from .normalize import normalize
from .profiles import DEFAULT_PROFILE
from .result_cap import cap_result
from .retrieval.schema_index import SchemaIndex
from .session import Message, SessionStore
from .tools.base import ToolContext

_logger = logging.getLogger(__name__)

# how many prior turns to replay each request (sliding window)
HISTORY_WINDOW = 12
# safety bound on tool-calling iterations per user turn
MAX_STEPS = 6
# cap-and-spill: bound tool-result size so a large query can't flood the
# context (per call) or accumulate across a turn (aggregate budget).
MAX_RESULT_CHARS = 40000       # per-result cap before truncation kicks in
TURN_RESULT_BUDGET = 150000    # aggregate cap across all tool results in a turn
RESULT_PREVIEW_ROWS = 30       # rows kept when truncating a list-shaped result
RESULT_PREVIEW_CHARS = 4000    # size of the character-preview fallback
RESULT_MIN_CHARS = 2000        # floor so every result gets at least a small preview
# values that confirm a pending write
PROCEED_VALUES = {"proceed", "yes", "y", "confirm", "ok", "go ahead"}
# values that abort it outright; anything else is treated as a change request
CANCEL_VALUES = {"cancel", "no", "n", "stop", "abort", "discard"}


class Orchestrator:
    """Drives one conversational turn end-to-end."""

    def __init__(self, env, profile=None, ui_context=None, registry=None):
        self.env = env
        self.llm = LLMClient(env)
        self.store = SessionStore(env)
        # Profile = system prompt + tool belt; resolved deterministically by
        # the caller (see core/profiles.py). Default preserves prior behavior.
        self.profile = profile or DEFAULT_PROFILE
        # The tool registry is normally assembled by the agent seam
        # (chatbot.agent._ai_build_registry) and passed in, so other modules can
        # contribute tools. When constructed directly (e.g. tests), fall back to
        # the profile's own builder.
        self.registry = registry if registry is not None else self.profile.build_registry()
        # Where the user is in the UI (action/model/view/studio) — consumed by
        # the upcoming UIContextFragment; stored here so Phase 2 is prompt-only.
        self.ui_context = ui_context if isinstance(ui_context, dict) else {}
        # running total of tool-result chars appended this turn (cap-and-spill
        # aggregate budget); reset per turn in _begin.
        self._turn_result_chars = 0

    def run(self, text, session_id, company_ids=None, interrupted=False):
        """Process one user turn and return ``{response, last_message}``."""
        if not self.llm.is_configured():
            return {
                'response': 'none',
                'last_message': (
                    '**AI is not configured.**\n\n'
                    'Please set up an LLM provider in **Settings → Cyllo AI**.'
                ),
            }

        _logger.info("[cyllo_ai] run session=%s interrupted=%s q=%r",
                     session_id, interrupted, (text or "")[:120])
        try:
            turn_usage = self._begin_turn_usage()
            state, ctx, terminal = self._begin(session_id, text, company_ids, interrupted)
            if terminal is not None:
                # A confirmed write failed — report it and end the turn.
                state.messages.append(Message(role="assistant", content=terminal))
                self.store.save(session_id, state)
                return {'response': 'none', 'last_message': terminal,
                        'chart_config': None, 'usage': turn_usage}
            return self._agent_loop(state, ctx, session_id, turn_usage)
        except UserError as e:
            # Deliberate, already-explained failure (e.g. the server cannot
            # reach the provider). One line, no traceback — the condition is
            # fully described by the message.
            _logger.warning("[cyllo_ai] run aborted session=%s: %s", session_id, e)
            return {'response': 'none', 'last_message': str(e)}
        except Exception as e:
            _logger.exception("[cyllo_ai] run failed session=%s: %s", session_id, str(e))
            return {'response': 'none', 'last_message': f'**Error:** {str(e)}'}

    def run_stream(self, text, session_id, company_ids=None, interrupted=False):
        """
        Streaming variant of :meth:`run` — streams the whole agent trajectory
        (narration text + tool activity + answer), not just the final output.

        Event types:
        - ``{"type": "delta", "text": ...}``        assistant text tokens (kept)
        - ``{"type": "tool_start", "id", "name", "label"}``   a tool began
        - ``{"type": "tool_end", "id", "name", "ok", "summary"}``   a tool finished
        - ``{"type": "confirm", "message": ...}``   a write awaits confirmation
        - ``{"type": "done", "last_message": ...}`` final answer (for persistence)
        - ``{"type": "error", "message": ...}``
        """
        if not self.llm.is_configured():
            msg = ('**AI is not configured.**\n\n'
                   'Please set up an LLM provider in **Settings → Cyllo AI**.')
            yield {'type': 'delta', 'text': msg}
            yield {'type': 'done', 'last_message': msg}
            return

        _logger.info("[cyllo_ai] stream session=%s interrupted=%s q=%r",
                     session_id, interrupted, (text or "")[:120])
        turn_usage = self._begin_turn_usage()
        try:
            state, ctx, terminal = self._begin(session_id, text, company_ids, interrupted)
        except UserError as e:
            _logger.warning("[cyllo_ai] stream setup aborted session=%s: %s", session_id, e)
            yield {'type': 'error', 'message': str(e)}
            return
        except Exception as e:
            _logger.exception("[cyllo_ai] stream setup failed session=%s: %s", session_id, str(e))
            yield {'type': 'error', 'message': str(e)}
            return

        if terminal is not None:
            # A confirmed write failed — report it and end the turn instead of
            # looping back to the model (which would re-plan another confirm).
            state.messages.append(Message(role='assistant', content=terminal))
            self.store.save(session_id, state)
            yield {'type': 'delta', 'text': terminal}
            yield {'type': 'done', 'last_message': terminal, 'usage': turn_usage}
            return

        tools = self.registry.tools()
        try:
            for step in range(MAX_STEPS):
                _logger.debug("[cyllo_ai] step %d session=%s history=%d msgs",
                              step, session_id, len(state.messages))
                messages = normalize(self._assemble(state))

                # Stream this step's text (narration or answer) as it arrives.
                assembled, step_text = None, []
                t0 = time.perf_counter()
                for ev_type, payload in self.llm.stream(messages, tools):
                    if ev_type == 'delta':
                        step_text.append(payload)
                        yield {'type': 'delta', 'text': payload}
                    elif ev_type == 'final':
                        assembled = payload or {}
                assembled = assembled or {'content': ''.join(step_text) or None, 'tool_calls': []}
                # Token usage is recorded centrally in LLMClient (into turn_usage
                # via env.context), covering tool-internal calls too.
                tool_calls = assembled.get('tool_calls') or []
                content = assembled.get('content')
                # Workflow trace only — the response content itself is logged by LLMClient.
                _logger.info("[cyllo_ai] turn %d session=%s tools=%s final=%s (%.0fms)",
                             step, session_id, [tc.get("name") for tc in tool_calls],
                             not tool_calls, (time.perf_counter() - t0) * 1000)

                if not tool_calls:
                    final_text = content if content is not None else ''.join(step_text)
                    state.messages.append(Message(role='assistant', content=final_text or ''))
                    self.store.save(session_id, state)
                    _logger.info("[cyllo_ai] stream done session=%s answer_len=%d tokens=%d",
                                 session_id, len(final_text or ''), turn_usage['total'])
                    yield {'type': 'done', 'last_message': final_text or '',
                           'usage': turn_usage}
                    return

                # Record the assistant's tool-calling turn (narration text kept).
                state.messages.append(Message(
                    role='assistant',
                    content=content or '',
                    tool_calls=[
                        {"id": tc["id"], "name": tc["name"], "arguments": tc.get("arguments") or {}}
                        for tc in tool_calls
                    ],
                ))

                # Execute each tool, surfacing activity to the user as it happens.
                confirm = yield from self._stream_tool_calls(state, ctx, tool_calls, session_id)
                if confirm is not None:
                    self.store.save(session_id, state)
                    yield {'type': 'confirm', 'message': confirm}
                    return

            self.store.save(session_id, state)
            last = next((m.content for m in reversed(state.messages)
                         if m.role == "assistant" and m.content), "")
            _logger.warning("[cyllo_ai] stream step budget exhausted session=%s", session_id)
            yield {'type': 'done',
                   'last_message': last or "I couldn't complete that within the step limit.",
                   'usage': turn_usage}
        except UserError as e:
            _logger.warning("[cyllo_ai] stream aborted session=%s: %s", session_id, e)
            yield {'type': 'error', 'message': str(e)}
        except Exception as e:
            _logger.exception("[cyllo_ai] stream failed session=%s: %s", session_id, str(e))
            yield {'type': 'error', 'message': str(e)}

    def _stream_tool_calls(self, state, ctx, tool_calls, session_id):
        """
        Execute tool calls, yielding ``tool_start``/``tool_end`` events.

        Returns (via generator return) a confirm message if a risky write must
        pause; otherwise ``None``. The risky write's tool-result is deferred to
        resume; read-only results are appended inline.
        """
        for tc in tool_calls:
            name, call_id, args = tc["name"], tc["id"], (tc.get("arguments") or {})
            tool = self.registry.get(name) if self.registry.has(name) else None
            label = (getattr(tool, "label", "") or name) if tool else name

            _logger.info("[cyllo_ai] tool_start session=%s name=%s args=%s",
                         session_id, name, list(args.keys()))
            yield {'type': 'tool_start', 'id': call_id, 'name': name, 'label': label}

            if tool is None:
                self._append_tool_result(state, call_id, name, {"error": f"Unknown tool: {name}"})
                yield {'type': 'tool_end', 'id': call_id, 'name': name,
                       'ok': False, 'summary': 'unknown tool'}
                continue

            t0 = time.perf_counter()
            try:
                out = tool.run(ctx, **args)
            except Exception as e:
                _logger.exception("[cyllo_ai] tool %s failed session=%s", name, session_id)
                self._append_tool_result(state, call_id, name, {"error": str(e)})
                yield {'type': 'tool_end', 'id': call_id, 'name': name,
                       'ok': False, 'summary': str(e)[:200]}
                continue

            if isinstance(out, dict) and out.get("__interrupt__"):
                state.pending = {
                    "tool_call_id": call_id,
                    "name": name,
                    "query": out.get("pending_query"),
                    "message": out.get("message", "Confirm this operation?"),
                }
                _logger.info("[cyllo_ai] confirm required session=%s name=%s", session_id, name)
                yield {'type': 'tool_end', 'id': call_id, 'name': name,
                       'ok': True, 'summary': 'awaiting confirmation'}
                return state.pending["message"]

            # Split any chart_config out to the UI; feed only the ack to the LLM.
            out, chart = self._split_chart(out)
            if chart is not None:
                yield {'type': 'chart', 'config': chart}
            # Same for chart suggestions: the cards go to the UI, the LLM gets an ack.
            out, suggestions = self._split_suggestions(out)
            if suggestions is not None:
                yield {'type': 'suggestions', 'items': suggestions}
            # And for a direct chart edit: the UI applies it, the LLM gets an ack.
            out, apply_edit = self._split_apply_edit(out)
            if apply_edit is not None:
                yield {'type': 'apply_edit', 'edit': apply_edit}
            # A widget to render in the chat (e.g. the quick-dashboard builder).
            out, widget = self._split_widget(out)
            if widget is not None:
                yield {'type': 'widget', 'widget': widget}
            # A patch to the quick-dashboard builder the user is curating.
            out, apply_qd = self._split_apply_qd(out)
            if apply_qd is not None:
                yield {'type': 'apply_qd', 'patch': apply_qd}
            # An edit applied to a live (created) dashboard — reload it.
            out, apply_dash = self._split_apply_dash(out)
            if apply_dash is not None:
                yield {'type': 'apply_dash', 'patch': apply_dash}
            self._append_tool_result(state, call_id, name, out)
            ok = not (isinstance(out, dict) and out.get("error"))
            _logger.info("[cyllo_ai] tool_end session=%s name=%s ok=%s %.0fms",
                         session_id, name, ok, (time.perf_counter() - t0) * 1000)
            yield {'type': 'tool_end', 'id': call_id, 'name': name,
                   'ok': ok, 'summary': self._tool_summary(out)}
        return None

    @staticmethod
    def _split_chart(out):
        """If a tool result carries a chart_config (and is not an error), return
        (llm_ack, chart_config); otherwise (out, None) — errors pass through intact."""
        if isinstance(out, dict) and out.get("chart_config") and not out.get("error"):
            ack = {"message": out.get("message", "Chart rendered and shown to the user.")}
            return ack, out["chart_config"]
        return out, None

    @staticmethod
    def _split_suggestions(out):
        """If a tool result carries chart `suggestions` (and is not an error),
        return (llm_ack, suggestions); otherwise (out, None). The cards are shown
        to the user directly, so the LLM only needs a short acknowledgement."""
        if isinstance(out, dict) and out.get("suggestions") and not out.get("error"):
            n = len(out["suggestions"])
            ack = {"message": out.get("message",
                                      f"Showed the user {n} chart suggestion(s) as apply cards.")}
            return ack, out["suggestions"]
        return out, None

    @staticmethod
    def _split_apply_edit(out):
        """If a tool result carries an `apply_edit` directive (and is not an
        error), return (llm_ack, edit); otherwise (out, None). The UI applies the
        edit to the live chart, so the LLM only needs a short acknowledgement."""
        if isinstance(out, dict) and out.get("apply_edit") and not out.get("error"):
            ack = {"message": out.get("message", "Applied the change to the chart.")}
            return ack, out["apply_edit"]
        return out, None

    @staticmethod
    def _split_widget(out):
        """If a tool result carries a `widget` to render in the chat (and is not
        an error), return (llm_ack, widget); otherwise (out, None). The UI renders
        the widget in a bot message, so the LLM only needs a short ack."""
        if isinstance(out, dict) and out.get("widget") and not out.get("error"):
            ack = {"message": out.get("message", "Opened the builder for the user.")}
            return ack, out["widget"]
        return out, None

    @staticmethod
    def _split_apply_qd(out):
        """If a tool result carries an `apply_qd` patch for the quick-dashboard
        builder (and is not an error), return (llm_ack, patch); otherwise
        (out, None). The UI applies the patch to the live builder widget, so the
        LLM only needs a short acknowledgement."""
        if isinstance(out, dict) and out.get("apply_qd") and not out.get("error"):
            ack = {"message": out.get("message", "Updated the dashboard builder.")}
            return ack, out["apply_qd"]
        return out, None

    @staticmethod
    def _split_apply_dash(out):
        """If a tool result carries an `apply_dash` directive (a live-dashboard
        edit was written and the view must reload), return (llm_ack, directive);
        otherwise (out, None). The write already happened server-side; the UI
        just reloads, so the LLM only needs a short acknowledgement."""
        if isinstance(out, dict) and out.get("apply_dash") and not out.get("error"):
            ack = {"message": out.get("message", "Updated the dashboard.")}
            return ack, out["apply_dash"]
        return out, None

    @staticmethod
    def _tool_summary(out):
        """Short, log/UI-friendly summary of a tool result."""
        if isinstance(out, str):
            return (out[:80] + '…') if len(out) > 80 else out
        if isinstance(out, dict):
            if out.get("error"):
                return f"error: {str(out['error'])[:120]}"
            return out.get("message") or "ok"
        return "ok"

    def _begin(self, session_id, text, company_ids, interrupted):
        """Shared setup: load session, resume pending or append the user turn."""
        self._turn_result_chars = 0  # reset the per-turn cap-and-spill budget
        state = self.store.load(session_id)
        if company_ids:
            state.company_ids = company_ids
        company_scope = state.company_ids or self.env.company.ids

        terminal = None
        if interrupted and state.pending:
            terminal = self._resume_pending(state, text)
            user_query = self._last_user_query(state, text)
        else:
            if state.pending:
                # The user moved on without deciding (new message, not a
                # confirm). Close the dangling tool call — an assistant
                # tool_call without a result is rejected by providers (400).
                self._append_tool_result(
                    state, state.pending["tool_call_id"],
                    state.pending.get("name", "write_records"),
                    {"message": "Not executed — the user moved on without "
                                "confirming. Treat it as cancelled."})
                state.pending = None
            state.messages.append(Message(role="user", content=text))
            user_query = text

        ctx = ToolContext(
            env=self.env,
            user_query=user_query,
            company_ids=company_scope,
            session_id=session_id,
            ui_context=self.ui_context,
        )
        # Built once per turn → byte-identical across loop steps (cache-friendly).
        self._schema_ctx = self._build_schema_block(user_query)
        return state, ctx, terminal

    def _build_schema_block(self, user_query):
        """
        Tiered schema injection: names-only for all candidate models, compact
        field lists for the top keyword hits (+ Studio ``x_`` customs) only.
        Standard-model fields the LLM already knows are NOT injected; the
        ``get_model_fields`` tool is the escape hatch for everything else.
        """
        try:
            schema = SchemaIndex(self.env)
            candidates = self.env['chatbot.tools']._candidate_models(user_query)
            hits = [h['model'] for h in schema.search_models(user_query, limit=8)]
            detail = [m for m in candidates if m in hits][:5]
            detail += [m for m in candidates if m.startswith('x_') and m not in detail]
            lines = [
                "<cyllo_schema>",
                "Candidate models for this request: " + ", ".join(candidates),
            ]
            if detail:
                lines.append("Key fields:")
                for m in detail:
                    lines.append(f"- {m}: {schema.compact_fields(m, max_fields=30)}")
            lines.append("For any other model or full field details, call get_model_fields(model).")
            lines.append("</cyllo_schema>")
            return "\n".join(lines)
        except Exception as e:
            _logger.debug("[cyllo_ai] schema block build failed: %s", e, exc_info=True)
            return ""

    # -- agent loop ----------------------------------------------------------

    def _agent_loop(self, state, ctx, session_id, turn_usage=None):
        tools = self.registry.tools()
        chart_config = None
        # turn_usage is the shared sink seeded by _begin_turn_usage; LLMClient
        # records every call (loop + tool-internal) into it directly.
        turn_usage = turn_usage if turn_usage is not None else self._new_usage()

        for step in range(MAX_STEPS):
            messages = normalize(self._assemble(state))
            _logger.debug("[cyllo_ai] turn %d session=%s sending %d msgs roles=%s",
                          step, session_id, len(messages), [m.role for m in messages])
            resp = self.llm.complete_with_tools(messages, tools)
            tool_calls = resp.get("tool_calls") or []
            content = resp.get("content")
            # Workflow trace only — the response content itself is logged by LLMClient.
            _logger.info("[cyllo_ai] turn %d session=%s tools=%s final=%s",
                         step, session_id, [tc.get("name") for tc in tool_calls],
                         not tool_calls)

            if not tool_calls:
                state.messages.append(Message(role="assistant", content=content or ""))
                self.store.save(session_id, state)
                return {'response': 'none', 'last_message': content or "",
                        'chart_config': chart_config, 'usage': turn_usage}

            # Record the assistant's tool-calling turn.
            state.messages.append(Message(
                role="assistant",
                content=content or "",
                tool_calls=[
                    {"id": tc["id"], "name": tc["name"], "arguments": tc.get("arguments") or {}}
                    for tc in tool_calls
                ],
            ))

            pending, chart = self._dispatch_tool_calls(state, ctx, tool_calls)
            if chart is not None:
                chart_config = chart
            if pending:
                # A risky write is awaiting confirmation — pause the turn.
                state.pending = pending
                self.store.save(session_id, state)
                return {'response': pending["message"], 'last_message': content or "",
                        'chart_config': chart_config, 'usage': turn_usage}

        # Step budget exhausted.
        self.store.save(session_id, state)
        last = next((m.content for m in reversed(state.messages)
                     if m.role == "assistant" and m.content), "")
        return {
            'response': 'none',
            'last_message': last or "I couldn't complete that within the step limit.",
            'chart_config': chart_config,
            'usage': turn_usage,
        }

    def _dispatch_tool_calls(self, state, ctx, tool_calls):
        """
        Execute each tool call, appending a tool-result message.

        Returns ``(pending, chart_config)``: ``pending`` is set if a risky write
        must pause for confirmation (its result deferred until resume);
        ``chart_config`` is the last chart produced this batch (or None).
        """
        pending = None
        chart_config = None
        for tc in tool_calls:
            name, call_id, args = tc["name"], tc["id"], (tc.get("arguments") or {})

            if not self.registry.has(name):
                self._append_tool_result(state, call_id, name, {"error": f"Unknown tool: {name}"})
                continue

            try:
                out = self.registry.get(name).run(ctx, **args)
            except Exception as e:
                _logger.exception("Tool %s failed: %s", name, str(e))
                self._append_tool_result(state, call_id, name, {"error": str(e)})
                continue

            if isinstance(out, dict) and out.get("__interrupt__"):
                # Defer this write; its tool-result is added on resume.
                pending = {
                    "tool_call_id": call_id,
                    "name": name,
                    "query": out.get("pending_query"),
                    "message": out.get("message", "Confirm this operation?"),
                }
                continue

            out, chart = self._split_chart(out)
            if chart is not None:
                chart_config = chart
            # Peel suggestions / edit directives off the LLM-facing result too
            # (non-stream can't act on them, but the model still needs only the ack).
            out, _suggestions = self._split_suggestions(out)
            out, _apply_edit = self._split_apply_edit(out)
            out, _widget = self._split_widget(out)
            out, _apply_qd = self._split_apply_qd(out)
            out, _apply_dash = self._split_apply_dash(out)
            self._append_tool_result(state, call_id, name, out)
        return pending, chart_config

    # -- confirmation / resume ----------------------------------------------

    def _resume_pending(self, state, text):
        """Apply the user's decision to a paused write, then clear pending.

        Three outcomes:
        - proceed word  -> run the confirmed operation;
        - cancel word   -> abort, nothing else;
        - anything else -> treat as a CHANGE REQUEST: abort the pending draft
          and replay the text as a user message so the agent revises and
          previews again (otherwise the edit would be silently swallowed).

        Returns a *terminal message* (str) when a confirmed operation FAILED:
        the caller ends the turn with it instead of looping back to the model,
        which would otherwise re-plan the same write into another confirmation.
        Returns None in every other case (normal generation continues).
        """
        pending = state.pending
        decision = (text or "").strip().lower()
        proceed = decision in PROCEED_VALUES
        is_edit = not proceed and decision not in CANCEL_VALUES
        _logger.info("[cyllo_ai] resume pending name=%s proceed=%s edit=%s",
                     pending.get("name"), proceed, is_edit)
        terminal = None
        if proceed:
            # dispatch by the tool that paused: email/SMS have their own
            # confirmed executors; everything else is sandboxed CRUD.
            executors = {
                "send_email": self.env['chatbot.tools'].execute_confirmed_email,
                "send_text": self.env['chatbot.tools'].execute_confirmed_text,
                "send_internal_message":
                    self.env['chatbot.tools'].execute_confirmed_internal_message,
            }
            execute = executors.get(pending.get("name"),
                                    self.env['chatbot.tools'].execute_confirmed_crud)
            out = execute(pending["query"])
            # A confirmed write that failed ends the turn: report the failure
            # rather than letting the model re-plan it into another confirm loop.
            if isinstance(out, dict) and out.get("error"):
                terminal = out["error"]
                _logger.info("[cyllo_ai] confirmed write failed, ending turn: %s",
                             terminal)
        elif is_edit:
            out = {"message": "Not executed — the user requested changes instead. "
                              "Read their next message and produce a revised draft "
                              "(call the same tool again with the updated content, "
                              "same recipient). If their message is itself a full "
                              "draft body, use it as the new content verbatim."}
        else:
            out = {"message": "Cancellation confirmed. Nothing was sent or changed."}
        self._append_tool_result(state, pending["tool_call_id"],
                                 pending.get("name", "write_records"), out)
        state.pending = None
        if is_edit:
            state.messages.append(Message(role="user", content=text))
        return terminal

    # -- helpers -------------------------------------------------------------

    @staticmethod
    def _new_usage():
        return {'prompt': 0, 'completion': 0, 'total': 0}

    def _begin_turn_usage(self):
        """Seed a per-turn token sink in env.context and bind the LLM client.

        Every LLMClient call this turn — the agent loop's AND any tool-internal
        call (e.g. analytic_record's SQL generation) — records into this same
        mutable dict, giving a true whole-turn total. Returns the dict; the
        caller reads it when the turn ends. Safe to mutate self.env: a fresh
        Orchestrator is built per turn.
        """
        usage = self._new_usage()
        self.env = self.env(context=dict(self.env.context, cyllo_ai_usage=usage))
        self.llm.env = self.env
        return usage

    def _append_tool_result(self, state, call_id, name, out):
        """Append a tool result, bounded by the cap-and-spill budget.

        Each result is capped to the smaller of the per-result cap and what is
        left of the per-turn aggregate budget (never below a small floor, so a
        result always gets at least a preview). Oversized results are truncated
        with an explicit hint rather than flooding the context.
        """
        remaining = TURN_RESULT_BUDGET - self._turn_result_chars
        max_chars = max(RESULT_MIN_CHARS, min(MAX_RESULT_CHARS, remaining))
        content, capped = cap_result(
            out, max_chars, RESULT_PREVIEW_ROWS, RESULT_PREVIEW_CHARS)
        self._turn_result_chars += len(content)
        if capped:
            _logger.info("[cyllo_ai] tool result capped name=%s len=%d turn_total=%d",
                         name, len(content), self._turn_result_chars)
        state.messages.append(Message(
            role="tool", content=content, tool_call_id=call_id, name=name,
        ))

    @staticmethod
    def _last_user_query(state, fallback):
        return next((m.content for m in reversed(state.messages) if m.role == "user"), fallback)

    def _assemble(self, state):
        """Build the message list: system + context fragments + schema + history."""
        fragments = [
            DateContextFragment(self.env),
            UserContextFragment(self.env),
            CompanyContextFragment(self.env, state.company_ids),
            UIContextFragment(self.env, self.ui_context),
            MentionContextFragment(self.env, self.ui_context),
            ChartContextFragment(self.env, self.ui_context),
            QuickDashboardContextFragment(self.env, self.ui_context),
            LiveDashboardContextFragment(self.env, self.ui_context),
        ]
        rendered = "\n".join(r for r in (f.render() for f in fragments) if r)
        parts = [self.profile.system_prompt, rendered]
        if getattr(self, "_schema_ctx", ""):
            parts.append(self._schema_ctx)
        messages = [Message(role="user", content="\n\n".join(parts))]
        messages.extend(state.messages[-HISTORY_WINDOW:])
        return messages
