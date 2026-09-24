/** @odoo-module **/
import { Component, useState, useEffect, markup, useRef, onMounted, onWillUnmount, onPatched, onWillStart, onWillUpdateProps } from "@odoo/owl";
import { reactive } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService, useBus } from "@web/core/utils/hooks";
import { browser } from "@web/core/browser/browser";
import { ChatUser } from "../chat_user/chat_user";
import { ChatResponse } from "../chat_response/chat_response";
import { ChatSidebar } from "../chat_sidebar/chat_sidebar";

const REPORT_OPTIONS = [
    "Trial Balance", "General Ledger", "Partner Ledger", "Aged Receivable",
    "Aged Payable", "Tax Report", "Cash Book", "Bank Book",
    "Profit and Loss", "Balance Sheet",
].map((name, i) => ({ id: i + 1, name }));

// Same pattern ChatResponse#confirmCard matches to detect a confirm-card
// turn. Needed here too (history mapping, below) to decide whether `text` is
// the card's own preview markdown rather than an answer worth rendering as a
// paragraph. NOT the same thing as the persisted `interrupted` flag: that
// flips to false the moment the card is resolved (proceed/cancel), but the
// card itself keeps rendering from `text` regardless — see confirmCard's own
// docstring. Matching on shape, not on resolved-state, is what stays correct
// on every reload.
const CONFIRM_CARD_RE = /\*\*Action:\*\*\s*\w+\s*—\s*.+?\s*\([\w.]+\)/;

// Persisted launcher position + drag tuning.
const ICON_POS_KEY = "cyllo_chatbot_icon_pos";
const ICON_SIZE = 60;       // minimized launcher is a fixed 60×60 circle
const DRAG_THRESHOLD = 5;   // px of movement before a press becomes a drag
const VIEWPORT_MARGIN = 4;  // keep the launcher this far from the edges

/**
 * Slash-command registry. A command with a `picker` runs a structured flow:
 * select it -> it becomes a chip in the input card -> a picker pops up to
 * choose the target (partner via name_search, or a static list) -> the user
 * types the content -> Enter sends a deterministic message to the agent.
 * For email/SMS the agent then drafts the message and the backend pauses
 * with a full preview the user must confirm before anything is sent.
 * Commands flagged `studio: true` only appear when ui_context says Studio is
 * active (none yet — Phase 4 adds them as plain array entries).
 */
// Longest excerpt select-to-quote will carry into a prompt.
const MAX_QUOTE_CHARS = 1000;

const SLASH_COMMANDS = [
    {
        key: "/email", label: "Send an email", chip: "Email",
        picker: { type: "partner", placeholder: "Search recipient…" },
        contentPlaceholder: "Write your message — Cyllo drafts the email and previews it before sending",
        buildMessage: (sel, text) => text
            ? `Send an email to "${sel.name}" (partner id ${sel.id}). Email content: ${text}`
            : null,
    },
    {
        key: "/text", label: "Send a text message (SMS)", chip: "SMS",
        picker: { type: "partner", placeholder: "Search recipient…" },
        contentPlaceholder: "Write the SMS text — you'll see a preview before it is sent",
        buildMessage: (sel, text) => text
            ? `Send a text message (SMS) to "${sel.name}" (partner id ${sel.id}). Message: ${text}`
            : null,
    },
    {
        key: "/message", label: "Send an internal message", chip: "Message",
        picker: { type: "user", placeholder: "Search user…" },
        contentPlaceholder: "Write your message — you'll see a preview before it is sent",
        buildMessage: (sel, text) => text
            ? `Send an internal message to "${sel.name}" (user id ${sel.id}). Message: ${text}`
            : null,
    },
    {
        key: "/report", label: "Open an accounting report", chip: "Report",
        picker: { type: "static", placeholder: "Search report…", options: REPORT_OPTIONS },
        contentPlaceholder: "Add a period or filters (optional), e.g. 'for last month' — Enter to open",
        buildMessage: (sel, text) =>
            `Show the ${sel.name.toLowerCase()} ${text || "for this month"}`,
    },
];


export class ChatBot extends Component {
    static props = {
        action: { type: Object, optional: true },
        actionId: { type: [Number, String], optional: true },
        className: { type: String, optional: true },
    };

    setup() {
        super.setup(...arguments);
        this.user = useService("user");
        this.orm = useService("orm");
        this.company = useService("company");
        this.inputWrapper = useRef('input-wrapper');
        this.composerRef = useRef('composer');
        this.mentionRecordInput = useRef('mention-record-input');
        this.busService = this.env.services.bus_service;
        this.upperScroll = useRef('upperScroll')
        const { origin } = browser.location;
        const { userId } = this.user;
        this.childChartApis = {};
        this.isDestroyed = false;
        const currentUrl = new URL(window.location.href);
        this.state = useState({
            messages: [],
            chatOn: false,
            inputText: "",
            isTyping: false,
            isGenerating: false,
            playingMessageId: null,   // which bot response is being read aloud
            activityStatus: "",
            // Provider/model shown on the composer chip. Fetched from a
            // purpose-built route that never returns the API key.
            modelLabel: "",
            providerLabel: "",
            // Select-to-quote. `quoteBtn` is the transient floating "Reply"
            // affordance ({text, x, y} in viewport coords); `quotedText` is the
            // excerpt the user committed to, shown above the composer.
            quoteBtn: null,
            quotedText: "",
            minimized: true,
            user_image: `${origin}/web/image?model=res.users&field=avatar_128&id=${userId}`,
            isDragging: false,
            interrupted: false,
            dragStyle: "bottom: 20px;",
            session_id: "",
            currentTitle: "Cyllo AI",
            chartNeedsRefresh: false,
            isRecording: false,
            isProcessingVoice: false,
            convertVoice: false,
            recordingStart: 0,
            recordingElapsed: 0,
            recordingDisplay: "00:00",
            sessions: [],
            sessionsLoading: false,
            historyOpen: false,
            slashOpen: false,
            slashFilter: "",
            slashIndex: 0,
            activeCommand: null,   // {key, chip, selection: {id, name}|null}
            // @ mention menu: pick a screen (model + its default view) to
            // attach as context, independent of wherever the user actually
            // is right now. Unlike slash commands this can trigger anywhere
            // in the text, not just at the start.
            mentionOpen: false,
            mentionFilter: "",
            mentionIndex: 0,
            mentionOptions: [],
            mentionLoading: false,
            // Second step of the @ flow: once a screen is picked, optionally
            // pin it to one specific record ("Contact" -> "Cyllo") via a
            // name_search on that screen's model. Skippable — the mention
            // still works as a plain model+view reference either way.
            mentionRecordOpen: false,
            mentionRecordOptions: [],
            mentionRecordIndex: 0,
            mentionRecordLoading: false,
            pendingMentions: [],   // [{model, viewType, name, actionId, resId, recordName}]
            pickerOpen: false,
            pickerOptions: [],
            pickerIndex: 0,
            pickerLoading: false,
            // Current-screen context chip. `uiContext` mirrors getUiContext()
            // augmented with display labels; `contextEnabled` is the user's
            // on/off toggle (on by default, persists across navigation for the
            // session — resets only on a full page reload).
            contextEnabled: true,
            uiContext: null,       // {model, modelLabel, resId, recordName, viewType}|null
            // Contextual nudge bubble shown beside the minimized launcher.
            // Other modules set it via the CY_AI:NUDGE bus event ({label, key})
            // and clear it with CY_AI:CLEAR_NUDGE; clicking it re-broadcasts
            // CY_AI:NUDGE_CLICKED so the originating module can react. Generic —
            // the chatbot only renders/positions it beside its (draggable) icon.
            nudge: null,           // {label, key}|null
            // Docked mode: on a "dock context" (a screen registered in the
            // "cyllo_ai.dock_contexts" registry, e.g. the analytics sheet), the
            // EXPANDED chat renders as a flush-right rail instead of the floating
            // modal. Derived from the current screen on every navigation (see
            // _refreshDockState), so it self-corrects — no lifecycle events. The
            // launcher (minimized owl) is unaffected.
            docked: false,
            // Host-contributed offer button shown in the empty-state greeting
            // ({label, key}); set via CY_AI:SET_OFFER, cleared by CY_AI:CLEAR_OFFER.
            // Clicking it broadcasts CY_AI:CHAT_ACTION so the host can respond
            // (e.g. analytics generates chart suggestions). Generic.
            offer: null,
            // True between the offer click and the host's reply (a pushed
            // message) — drives the button's loading state.
            offerLoading: false,
            isStudio: currentUrl.searchParams.get("studio") == 1 ? true : false,
        })
        // Contextual-nudge bus wiring (see state.nudge above).
        useBus(this.env.bus, "CY_AI:NUDGE", (ev) => { this.state.nudge = ev.detail || null; });
        useBus(this.env.bus, "CY_AI:CLEAR_NUDGE", () => { this.state.nudge = null; });
        // Hide the floating bubble while a full-screen client action (ChatBotScreen)
        // is mounted.  A reference counter lets nested/overlapping callers work safely.
        this._bubbleHideCount = 0;
        useBus(this.env.bus, "CY_AI:HIDE_BUBBLE", () => {
            this._bubbleHideCount++;
            this.state.chatOn = false;
        });
        useBus(this.env.bus, "CY_AI:SHOW_BUBBLE", () => {
            this._bubbleHideCount = Math.max(0, this._bubbleHideCount - 1);
            if (this._bubbleHideCount === 0) {
                // Restore only when the config said the widget was on.
                this.state.chatOn = !!this.state.aiConfigured;
            }
        });
        // Docking is derived from the current screen (see _refreshDockState),
        // not from bus events — so it self-corrects on every navigation.
        // Split layout: mark the body while the chat is docked AND expanded, so
        // the host screen (e.g. the analytics sheet) reserves a right gutter and
        // reflows beside the chat instead of being overlaid. Removed on
        // minimize/undock/unmount (the effect cleanup).
        useEffect(
            () => {
                const open = this.state.docked && !this.state.minimized;
                document.body.classList.toggle("cy-ai-docked-open", open);
                return () => document.body.classList.remove("cy-ai-docked-open");
            },
            () => [this.state.docked, this.state.minimized],
        );
        // Host offer + message injection (see state.offer above).
        useBus(this.env.bus, "CY_AI:SET_OFFER", (ev) => {
            const offer = ev.detail || null;
            this.state.offer = offer;
            // Auto-fresh: when a suggest context activates while a DIFFERENT
            // thread is open, start a clean one (the old thread is archived to
            // history) so stale cross-context content doesn't linger. Opt-in via
            // the offer's `autoFresh`; "on-change" only resets on a mode switch.
            if (offer?.autoFresh && offer.mode) {
                this._enterChatContext(offer.mode, "on-change");
            }
        });
        useBus(this.env.bus, "CY_AI:CLEAR_OFFER", () => { this.state.offer = null; });
        useBus(this.env.bus, "CY_AI:PUSH_MESSAGE", (ev) => { this._pushHostMessage(ev.detail || {}); });
        // Explain a host chart: expand the chat, keep its data as context (rides
        // in ui_context so follow-ups stay chart-aware), and ask the agent to
        // explain it — with the chart attached to the USER turn (see handleSend).
        useBus(this.env.bus, "CY_AI:EXPLAIN_CHART", async (ev) => {
            const { chart, chartContext } = ev.detail || {};
            await this._maximize_chatbot();
            // Fresh thread only when ENTERING the explain flow; exploring more
            // charts on the same dashboard appends to the one analysis session.
            this._enterChatContext("chart_explain", "on-change");
            this._hostChartContext = chartContext || null;
            // Maximizing re-renders the chat; wait for the input to mount
            // before sending, else handleSend runs against a null composer.
            for (let i = 0; i < 30 && !this.inputWrapper?.el; i++) {
                await new Promise((resolve) => requestAnimationFrame(resolve));
            }
            this._nextUserChart = chart || null;   // rendered inside the user message
            this.handleSend("Explain this chart — the key trends, notable highs "
                + "and lows, any anomalies, and the main takeaways.");
        });
        // Host screens can attach a structured payload (e.g. the analytics
        // sheet's available fields) that rides in the outgoing ui_context so
        // their own agent tools can read it. See getOutgoingUiContext.
        this._hostQueryContext = null;
        this._hostChartContext = null;   // the chart being discussed (explain flow)
        this._nextUserChart = null;      // chart to attach to the next user turn
        this._chatMode = null;           // purpose of the current thread (see _enterChatContext)
        // Live state of the quick-dashboard builder widget (tables + proposed
        // cards + name), published by the active widget so it rides in the
        // outgoing ui_context and the agent's edit tool can reference cards.
        this._qdContext = null;
        // Live state of a CREATED dashboard the user is viewing (config id +
        // its saved charts), published by the dashboard screen so the agent's
        // edit_dashboard tool can reference and change them.
        this._dashContext = null;
        useBus(this.env.bus, "CY_AI:SET_QUERY_CONTEXT", (ev) => { this._hostQueryContext = ev.detail || null; });
        useBus(this.env.bus, "CY_AI:CLEAR_QUERY_CONTEXT", () => { this._hostQueryContext = null; });
        useBus(this.env.bus, "CY_AI:QD_STATE", (ev) => { this._qdContext = ev.detail || null; });
        useBus(this.env.bus, "CY_AI:QD_CLEAR", () => { this._qdContext = null; });
        useBus(this.env.bus, "CY_AI:DASH_STATE", (ev) => { this._dashContext = ev.detail || null; });
        useBus(this.env.bus, "CY_AI:DASH_CLEAR", () => { this._dashContext = null; });
        this.rpc = useService("rpc");
        this.actionService = useService("action");
        // Record links in chat bubbles navigate in the SAME tab via the web
        // client (no reload, no new tab). Non-record links keep their default
        // behavior (new tab). Delegated on document so it survives re-renders.
        // Matches BOTH roots: ".chatbot-modal" (the floating popup) and
        // ".cy-ai-screen" (ChatBotScreen's full-screen mode, which replaces
        // the popup's root class with this one via its own template patch —
        // see chatbot_screen.xml). doAction below reuses the current tab's
        // action slot regardless of which one fired, and unmounting the
        // full-screen action naturally restores the floating bubble
        // (ChatBotScreen's onWillUnmount triggers CY_AI:SHOW_BUBBLE) — so
        // "same tab, back to popup mode" falls out for free once this guard
        // actually lets the click through.
        this.onChatLinkClick = (ev) => {
            const a = ev.target.closest && ev.target.closest("a");
            if (!a || !a.closest(".chatbot-modal, .cy-ai-screen")) return;
            // Normalize: the model sometimes prepends a (possibly invented)
            // domain to the relative /web# links — strip any origin so the
            // matchers below work on the path regardless.
            const href = (a.getAttribute("href") || "").replace(/^https?:\/\/[^/]*/, "");

            // Record links: open the form view in the same tab.
            const m = href.match(/^\/web#id=(\d+)&model=([\w.]+)/);
            if (m) {
                ev.preventDefault();
                ev.stopPropagation();
                this.actionService.doAction({
                    type: "ir.actions.act_window",
                    res_model: m[2],
                    res_id: parseInt(m[1], 10),
                    views: [[false, "form"]],
                    target: "current",
                });
                this._minimize_chatbot();
                return;
            }

            // Report/action links: open in the same tab, forwarding only the
            // whitelisted, format-checked deep-link filters (the href text is
            // model-generated — never forward arbitrary context keys).
            const am = href.match(/^\/web#action=(\d+)(?:&(.+))?$/);
            if (am) {
                ev.preventDefault();
                ev.stopPropagation();
                const dateRe = /^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$/;
                const idsRe = /^\d+(,\d+)*$/;
                const FILTER_SPECS = {
                    cyllo_date_from: dateRe,
                    cyllo_date_to: dateRe,
                    cyllo_journal_ids: idsRe,
                    cyllo_account_ids: idsRe,
                    cyllo_analytic_ids: idsRe,
                    cyllo_partner_ids: idsRe,
                    cyllo_target_move: /^(posted|draft)(,(posted|draft))*$/,
                };
                const additionalContext = {};
                const params = new URLSearchParams(am[2] || "");
                for (const [key, re] of Object.entries(FILTER_SPECS)) {
                    const v = params.get(key);
                    if (v && re.test(v)) {
                        additionalContext[key] = v;
                    }
                }
                this.actionService.doAction(parseInt(am[1], 10), { additionalContext });
                this._minimize_chatbot();
            }
        };
        onMounted(() => document.addEventListener("click", this.onChatLinkClick, true));
        onWillUnmount(() => document.removeEventListener("click", this.onChatLinkClick, true));
        // Keep the context chip in sync as the user navigates the web client.
        // The URL hash carries model/id/action, so hashchange is a reliable,
        // cheap navigation signal. The chip DATA refreshes on every change; the
        // contextEnabled flag is deliberately NOT reset (persists for the session).
        this.onContextHashChange = () => this.refreshContextChip();
        onMounted(() => {
            window.addEventListener("hashchange", this.onContextHashChange);
            this.refreshContextChip();
        });
        onWillUnmount(() => window.removeEventListener("hashchange", this.onContextHashChange));
        this.chartDiv = useRef('echart')
        this.chatbotDiv = useRef("chatbotDiv")
        this.messageContainerRef = useRef("messageContainer");
        this.inputWrapper = useRef('input-wrapper')
        this.onInterruptResponse = this.onInterruptResponse.bind(this);
        this.onMessageBound = this.onMessage.bind(this);

        this.sessionRT = reactive({
            typing: {},          // { [sessionId]: boolean }
            pendingReq: {},      // { [sessionId]: requestId }
            pendingMsgs: {},     // { [sessionId]: Array<pendingMsg> }
        });

        // Initialize session BEFORE onWillStart - now tracking active company IDs
        this.lastActiveCompanyIds = this._getActiveCompanyIds();
        this._initSessionForCompanies();

        // The whole body is guarded. ChatBot is a ROOT main component, so any
        // rejection here propagates into the Owl lifecycle and blanks the entire
        // Odoo backend — an assistant that cannot start must degrade to "no
        // assistant", never take the ERP down with it. (This is not theoretical:
        // an offline browser meant `marked` never loaded, parseMarkdown threw
        // while mapping history, and the whole webclient went blank.)
        onWillStart(async () => {
            try {
                this.busService.addChannel("cyllo_channel");
                this.channel = "cyllo_ai_config"
                this.busService.addChannel(this.channel)
                this.busService.addEventListener("notification", this.onMessageBound)
                if (this.isDestroyed || this.__owl__?.status === 3) return;
                let cyllo_ai_widget = null
                try {
                    cyllo_ai_widget = await this.rpc('/cyllo/get_ai_widget_enabled');
                    if (!this.isDestroyed) {
                        this.state.aiConfigured = cyllo_ai_widget === '1';
                    }
                } catch (err) {
                    console.error("Error fetching config", err);
                }
                try {
                    const label = await this.rpc('/cyllo/get_model_label');
                    if (!this.isDestroyed && label && label.model) {
                        this.state.modelLabel = label.model;
                        this.state.providerLabel = label.provider || "";
                    }
                } catch (err) {
                    // Chrome only — never let this block the chat from opening.
                    console.debug("Cyllo AI: model label unavailable", err);
                }
                this.state.chatOn = cyllo_ai_widget === '1';
                const companyIds = this._getActiveCompanyIds();
                const history = await this.rpc("/chatbot/get_conversation", {
                    session_id: this.state.session_id,
                    company_ids: companyIds
                });

                this.state.messages = (history || []).map((msg, index) => {
                    let htmlContent = "";
                    if (msg.from === "bot") {
                        // Confirm-card turns store the card's own preview
                        // markdown as `text` — chatbot.history has no separate
                        // field for whatever narration preceded the tool call,
                        // so rendering `text` into html here would just
                        // reprint the card's fields as a plain paragraph above
                        // it. Checked by shape (CONFIRM_CARD_RE), NOT by
                        // `msg.interrupted` — that flag resolves to false once
                        // the card is handled, but the card keeps rendering
                        // from `text` either way (see confirmCard's own
                        // docstring), so it flipping must not bring the
                        // paragraph back. `msg.html` is never persisted
                        // either, so this deliberately renders no lead
                        // paragraph on reload rather than duplicating the card.
                        htmlContent = (msg.text && !CONFIRM_CARD_RE.test(msg.text))
                            ? markup(this.parseMarkdown(msg.text))
                            : (msg.html || "");
                    } else {
                        // The user's own text is NOT markdown, so it must not be run
                        // through the renderer. Doing so wrapped it in <p> and added
                        // marked's trailing newline, which `white-space: pre-wrap` on
                        // the pill then drew as a real blank line — every reloaded
                        // user message came back a line taller than it was sent. It
                        // also turned *word* into italics the user never asked for.
                        // Leaving it as text makes this path identical to the live
                        // one, where ChatUser escapes it via t-out.
                        htmlContent = msg.html || "";
                    }
                    const safeId = msg.id ? msg.id : `temp_${msg.timestamp || Date.now()}_${index}`;
                    return {
                        id: safeId,
                        from: msg.from,
                        html: htmlContent,
                        text: msg.text,
                        chart_config: msg.chart_config || null,
                        chart: msg.chart || null,
                        interrupted: msg.interrupted,
                        timestamp: msg.timestamp,
                        usage: msg.usage || null,
                        steps: msg.thinking?.steps || null,
                        thinkingMs: msg.thinking?.ms || 0,
                    };
                });
                if (this.state.messages.length) {
                    const title = await this.orm.call(
                        "chatbot.history", "get_session_title", [this.state.session_id]
                    );
                    if (title) {
                        this.state.currentTitle = title;
                    }
                }
            } catch (err) {
                // Leave whatever state was reached; the widget simply shows an empty
                // conversation rather than preventing the backend from rendering.
                console.error("Cyllo AI: startup failed, continuing without it", err);
            }
        });
        onWillUpdateProps((nextProps) => {
            // Check if chart_config has changed
            if (JSON.stringify(nextProps.chart_config) !== JSON.stringify(this.props.chart_config)) {
                this.baseChartConfig = nextProps.chart_config ? JSON.parse(JSON.stringify(nextProps.chart_config)) : null;
                this.state.chart_config = this.baseChartConfig;
                setTimeout(() => {
                    this.initChart();
                }, 0);
            }
        });
        this._onIconResize = () => {
            // Keep a dragged launcher on-screen when the window is resized.
            if (this.state.minimized && this.iconPos) this._applyIconStyle();
        };
        onMounted(() => {
            window.addEventListener('keydown', this.onKeyDown.bind(this));
            document.addEventListener("mousedown", this.handleClickOutside.bind(this));
            window.addEventListener("resize", this._onIconResize);
            // Restore a previously dragged launcher position.
            const saved = this._loadIconPos();
            if (saved) { this.iconPos = saved; this._applyIconStyle(); }
            // Warm up the speech-synthesis voice list so the first play isn't silent.
            if (window.speechSynthesis) { try { window.speechSynthesis.getVoices(); } catch (_) { } }
            this.scrollToBottom();
        });
        onWillUnmount(() => {
            window.removeEventListener('keydown', this.onKeyDown);
            document.removeEventListener("mousedown", this.handleClickOutside);
            window.removeEventListener("resize", this._onIconResize);
            this.busService.removeEventListener("notification", this.onMessageBound);
            this.stopSpeaking();   // never leave speech playing after teardown
            this.isDestroyed = true;
        });
        onPatched(() => {
            this.scrollToBottom();
            if (this.state.chartNeedsRefresh) {
                this.refreshCharts();
                this.state.chartNeedsRefresh = false;
            }

            // Check if active company selection has changed
            const currentActiveIds = this._getActiveCompanyIds();
            if (!this._areCompanyIdsEqual(currentActiveIds, this.lastActiveCompanyIds)) {
                this.lastActiveCompanyIds = currentActiveIds;
                const newSession = this._initSessionForCompanies();
                this.loadSession(newSession);
                this.env.bus.trigger('LOAD_SIDEBAR', {});
            }
        });
    }

    // Helper to get active company IDs
    _getActiveCompanyIds() {
        return this.company?.activeCompanyIds || [];
    }

    // Helper to compare two arrays of company IDs
    _areCompanyIdsEqual(arr1, arr2) {
        if (arr1.length !== arr2.length) return false;
        const sorted1 = [...arr1].sort((a, b) => a - b);
        const sorted2 = [...arr2].sort((a, b) => a - b);
        return sorted1.every((val, index) => val === sorted2[index]);
    }

    // Generate storage key based on active company IDs
    _sessionStorageKey(companyIds) {
        // Create a consistent key from sorted company IDs
        const sortedIds = [...companyIds].sort((a, b) => a - b);
        const idsKey = sortedIds.length > 0 ? sortedIds.join('_') : 'no_company';
        return `chat_session_id_${idsKey}`;
    }

    // Initialize session for the current set of active companies
    _initSessionForCompanies() {
        const companyIds = this._getActiveCompanyIds();
        const key = this._sessionStorageKey(companyIds);
        let sessionId = localStorage.getItem(key);

        if (!sessionId) {
            const rand = crypto.randomUUID?.() || Math.random().toString(36).slice(2);
            // Include company IDs in session ID for clarity
            const idsStr = companyIds.length > 0 ? companyIds.sort((a, b) => a - b).join('_') : 'none';
            sessionId = `${idsStr}_${rand}`;
            localStorage.setItem(key, sessionId);
        }

        this.state.session_id = sessionId;
        return sessionId;
    }

    handleClickOutside(ev) {
        const chatbotEl = this.chatbotDiv.el;
        const sidebarEl = document.querySelector('.chatbot-history-sidebar');
        if (sidebarEl && sidebarEl.contains(ev.target)) {
            return;
        }
        // The "Conversations" hamburger opens/closes the drawer via its own
        // click handler (toggleHistory) — that click fires right after this
        // mousedown, so if this closed the drawer too, clicking the button
        // to close it would immediately reopen it. Exclude it.
        const isHistoryToggle = ev.target.closest('.cy-ai-icon-btn[title="Conversations"]');
        if (this.state.historyOpen && !isHistoryToggle) {
            this.state.historyOpen = false;
        }
        if (chatbotEl && !chatbotEl.contains(ev.target) && chatbotEl.querySelector('.chatbot-box')) {
            this._minimize_chatbot();
        }
    }

    onMessage({ detail: notifications }) {
        // The active config broadcasts {configured} on save.
        // Icon visibility is derived from that state — no extra RPC needed.
        const relevant = (notifications || []).filter(item => item.type === 'cyllo_ai_config');
        if (!relevant.length || this.isDestroyed) return;
        const payload = relevant[relevant.length - 1].payload || {};
        this.state.aiConfigured = !!payload.configured;
        this.state.chatOn = !!payload.configured;
    }

    registerChartApi(index, api) {
        this.childChartApis[index] = api;
    }
    refreshCharts() {
        for (const index in this.childChartApis) {
            const api = this.childChartApis[index];
            if (api && typeof api.resizeChart === 'function') {
                api.resizeChart();
            }
        }
    }

    scrollToBottom() {
        const el = this.upperScroll?.el || this.messageContainerRef?.el;
        if (!el) return;
        // Selecting text (e.g. to quote a bot reply, see onMessagesMouseUp)
        // writes to state.quoteBtn, which re-patches the component. Force-
        // scrolling on that patch would yank the view away from the very
        // text the user is selecting, so skip it while a selection is live.
        const sel = window.getSelection();
        if (sel && !sel.isCollapsed && el.contains(sel.anchorNode)) return;
        requestAnimationFrame(() => {
            el.scrollTop = el.scrollHeight;
        });
    }

    // -- draggable launcher icon ---------------------------------------------

    _loadIconPos() {
        try {
            const p = JSON.parse(localStorage.getItem(ICON_POS_KEY) || "null");
            if (p && Number.isFinite(p.x) && Number.isFinite(p.y)) return p;
        } catch (_) { /* ignore corrupt value */ }
        return null;
    }

    _saveIconPos(pos) {
        try { localStorage.setItem(ICON_POS_KEY, JSON.stringify(pos)); } catch (_) { }
    }

    /** Clamp a top-left position so the icon stays fully within the viewport. */
    _clampIconPos({ x, y }, w = ICON_SIZE, h = ICON_SIZE) {
        const m = VIEWPORT_MARGIN;
        const maxX = Math.max(m, window.innerWidth - w - m);
        const maxY = Math.max(m, window.innerHeight - h - m);
        return { x: Math.min(Math.max(x, m), maxX), y: Math.min(Math.max(y, m), maxY) };
    }

    /** Reflect the current state into dragStyle: a custom position only while
     *  minimized; maximized falls back to the CSS anchor (always on-screen). */
    _applyIconStyle() {
        if (!this.state.minimized) {
            // Docked: let the .docked CSS fully control position/size (flush
            // right rail) — no inline anchor. Otherwise the maximized window
            // keeps its original anchor (the .maximized CSS only sets `right`;
            // this inline `bottom` supplies the vertical anchor).
            this.state.dragStyle = this.state.docked ? "" : "bottom: 20px;";
            return;
        }
        if (!this.iconPos) {
            this.state.dragStyle = "bottom: 20px; right: 20px;";
            return;
        }
        // Clamp against the FIXED minimized size (60×60), not the live element
        // rect: on minimize this runs before the modal has collapsed from its
        // maximized size, so measuring it would mis-clamp the icon's position.
        const p = this._clampIconPos(this.iconPos, ICON_SIZE, ICON_SIZE);
        this.iconPos = p;
        this.state.dragStyle = `left:${p.x}px; top:${p.y}px; right:auto; bottom:auto;`;
    }

    onIconPointerDown(ev) {
        if (!this.state.minimized) return;
        const el = this.chatbotDiv?.el;
        if (!el) return;
        const r = el.getBoundingClientRect();
        this._drag = {
            pointerId: ev.pointerId,
            startX: ev.clientX, startY: ev.clientY,
            originX: r.left, originY: r.top, w: r.width, h: r.height,
            moved: false,
        };
        try { ev.currentTarget.setPointerCapture(ev.pointerId); } catch (_) { }
    }

    onIconPointerMove(ev) {
        const d = this._drag;
        if (!d || ev.pointerId !== d.pointerId) return;
        const dx = ev.clientX - d.startX;
        const dy = ev.clientY - d.startY;
        if (!d.moved && Math.hypot(dx, dy) < DRAG_THRESHOLD) return;
        d.moved = true;
        this.state.isDragging = true;
        this.iconPos = this._clampIconPos(
            { x: d.originX + dx, y: d.originY + dy }, d.w, d.h);
        this.state.dragStyle =
            `left:${this.iconPos.x}px; top:${this.iconPos.y}px; right:auto; bottom:auto;`;
    }

    /** Open the chat from the launcher. When the current screen offers a builder
     *  widget (e.g. an empty dashboard sets an offer carrying `widget`), land
     *  straight in that builder — same result as clicking the nudge — instead of
     *  the generic "How can I help you?" empty state. Only when the thread is
     *  empty, so it never barges into an existing conversation. */
    async _openChat() {
        // The launcher can sit minimized for a long time while other things
        // change the session server-side (another tab, a resumed/interrupted
        // turn finishing, the sidebar). This component only fetches history
        // once, in onWillStart — reopening otherwise just redisplays whatever
        // was already in memory, stale until a full page reload. Re-pull the
        // current session fresh, same as the company-switch refresh does.
        if (this.state.session_id) {
            await this.loadSession(this.state.session_id);
        }
        await this._maximize_chatbot();
        const offer = this.state.offer;
        if (offer?.widget && this.state.messages.length === 0) {
            if (offer.mode) {
                this._enterChatContext(offer.mode, offer.freshPolicy || "on-change");
            }
            this._pushHostMessage({ html: offer.intro || "", widget: offer.widget });
        }
    }

    onIconPointerUp(ev) {
        const d = this._drag;
        this._drag = null;
        this.state.isDragging = false;
        try { ev.currentTarget.releasePointerCapture(ev.pointerId); } catch (_) { }
        if (d && d.moved) {
            this._saveIconPos(this.iconPos);   // a drag → remember the spot
        } else {
            this._openChat();                  // a tap → open the chat
        }
    }

    onIconKeydown(ev) {
        if (ev.key === "Enter" || ev.key === " ") {
            ev.preventDefault();
            this._openChat();
        }
    }

    /** Escape text that is about to be handed to markup() as trusted HTML. */
    escapeHtml(text) {
        const M = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
        return String(text).replace(/[&<>"']/g, (c) => M[c]);
    }

    parseMarkdown(text) {
        if (typeof text !== 'string') return "";
        // `marked` comes from a CDN, so it is simply absent whenever the browser
        // is offline or the CDN is blocked. This used to throw — and because
        // this runs inside onWillStart of a ROOT main component, the exception
        // escaped into the Owl lifecycle and rendered the entire Odoo backend
        // blank, not just the chat. Degrade instead: the answer loses its
        // formatting, everything else keeps working.
        //
        // The fallback MUST escape. Every caller wraps this return value in
        // markup(), i.e. declares it trusted HTML, so emitting raw model output
        // here would be an injection point.
        let html;
        if (typeof window.marked?.parse !== "function") {
            console.warn("Cyllo AI: `marked` unavailable (offline or CDN blocked) — "
                + "rendering plain text.");
            html = this.escapeHtml(text).replace(/\n/g, "<br/>");
        } else {
            html = window.marked.parse(text);
            // Give every table its own scroll container. Only the table may
            // scroll sideways — putting the overflow on the answer instead
            // dragged the headings and prose along with it. A wrapper (rather
            // than making the table itself `display: block`) is what keeps
            // narrow tables stretching to full width: a block-level table
            // shrink-wraps to its content. Markdown cannot nest tables, so
            // this pairing is unambiguous.
            html = html
                .replace(/<table/g, '<div class="cy-ai-table-scroll"><table')
                .replace(/<\/table>/g, '</table></div>');
            // Record links must navigate reliably from inside the SPA: a
            // same-tab hash-only change (/web#id=...) won't reload the view,
            // so open chat links in a new tab instead.
            html = html.replace(/<a (?![^>]*\btarget=)/g, '<a target="_blank" rel="noopener noreferrer" ');
        }
        // The agent often echoes a "@[Name]" / "@[Name → Record]" mention
        // back in its own answer (see chat_user.js) — render it as the same
        // pill there too instead of leaving the raw brackets visible.
        return this.renderMentionPills(html);
    }

    /** Turn every "@[Name]" / "@[Name → Record]" marker in an HTML string
     *  into the shared .inline-mention-pill markup (see buildMentionPillNode
     *  in the composer, and ChatUser.mentionParts for the user-bubble side).
     *  Runs AFTER marked.parse, so name/record are plain text pulled out of
     *  the model's answer — not markup — and must be escaped before
     *  reinjection. */
    renderMentionPills(html) {
        return html.replace(/@\[([^\]]+)\]/g, (_, inner) => {
            const [name, recordName] = inner.split(" → ");
            let pill = `<span class="inline-mention-pill"><i class="ri-at-line"></i>`
                + this.escapeHtml((name || "").trim());
            if (recordName) {
                pill += `<i class="chip-sep ri-arrow-right-line"></i>`
                    + this.escapeHtml(recordName.trim());
            }
            return pill + `</span>`;
        });
    }

    async _close_chatbot() {
        this.env.chatbotClose()
    }

    async _minimize_chatbot() {
        this.state.isDragging = false;
        this.state.minimized = true;
        this.state.historyOpen = false;
        this.stopSpeaking();      // don't keep reading after the chat is closed
        this._applyIconStyle();   // restore the dragged launcher position
    }

    async openInScreen() {
        // Minimise the bubble so it doesn't overlap the screen view.
        await this._minimize_chatbot();

        const menuService = this.env.services.menu;

        // getAll() returns a flat array of every menu object with {id, xmlid, actionID, appID}.
        const chatMenu = menuService.getAll().find(
            (m) => m.xmlid === "cyllo_ai.menu_cyllo_ai_chatbot"
        );

        if (chatMenu) {
            // Broadcast the session id so ChatBotScreen can restore it after mount.
            if (this.state.session_id) {
                document.dispatchEvent(new CustomEvent("CY_AI:OPEN_SESSION", {
                    detail: this.state.session_id,
                }));
            }
            // selectMenu calls doAction(menu.actionID) + updates the URL/navbar app.
            await menuService.selectMenu(chatMenu);
        } else {
            // Fallback if menu lookup fails.
            await this.actionService.doAction("cyllo_ai.action_cyllo_ai", {
                additionalContext: { cy_ai_session_id: this.state.session_id },
            });
        }
    }

    async _maximize_chatbot() {
        this.state.minimized = true;
        this.refreshContextChip();   // chip reflects the screen at open time
        await new Promise(requestAnimationFrame);
        this.state.minimized = false;
        this._applyIconStyle();   // maximized → CSS anchor (clear inline pos)
        await new Promise(requestAnimationFrame);
        setTimeout(() => {
            this.state.chartNeedsRefresh = true;
            this.composerRef?.el?.focus();
        }, 500);
    }

    onKeyDown(ev) {
        // This same handler is also bound directly on the textarea and the
        // chatbot-box div (see the comment below) - the window-level binding
        // exists only as a safety net for those, not to react to typing
        // anywhere else in the backend, so it must bail out immediately for
        // any keydown that didn't originate inside the chatbot itself.
        if (this.chatbotDiv.el && !this.chatbotDiv.el.contains(ev.target)) {
            return;
        }
        // While a menu (slash or picker) is open, the keyboard drives it — in
        // particular Enter SELECTS, it must never send. stopPropagation() is
        // essential: this handler is attached on the textarea, the chatbot-box
        // div AND window, so without it the same keypress is processed again
        // by the outer handlers (which would see the menu closed and send).
        const menu = this.state.pickerOpen
            ? {
                items: this.state.pickerOptions, idxKey: "pickerIndex",
                select: (it) => this.selectPickerOption(it),
                close: () => this.cancelActiveCommand()
            }
            : this.state.mentionRecordOpen
                ? {
                    // Escape here SKIPS (commits the screen-only mention),
                    // it never fully cancels — picking a record is optional.
                    items: this.state.mentionRecordOptions, idxKey: "mentionRecordIndex",
                    select: (it) => this.selectMentionRecord(it),
                    close: () => this.skipMentionRecord()
                }
                : this.state.mentionOpen
                    ? {
                        items: this.state.mentionOptions, idxKey: "mentionIndex",
                        select: (it) => this.selectMention(it),
                        close: () => this.closeMentionMenu()
                    }
                    : this.state.slashOpen
                    ? {
                        items: this.filteredSlashCommands, idxKey: "slashIndex",
                        select: (it) => this.selectSlashCommand(it),
                        close: () => this.closeSlashMenu()
                    }
                    : null;
        if (menu) {
            const n = menu.items.length;
            if (ev.key === "ArrowDown" && n) {
                ev.preventDefault();
                ev.stopPropagation();
                this.state[menu.idxKey] = (this.state[menu.idxKey] + 1) % n;
                return;
            }
            if (ev.key === "ArrowUp" && n) {
                ev.preventDefault();
                ev.stopPropagation();
                this.state[menu.idxKey] = (this.state[menu.idxKey] - 1 + n) % n;
                return;
            }
            if (ev.key === "Enter" || ev.key === "Tab") {
                ev.preventDefault();
                ev.stopPropagation();
                if (n) menu.select(menu.items[this.state[menu.idxKey]]);
                return;
            }
            if (ev.key === "Escape") {
                ev.preventDefault();
                ev.stopPropagation();
                menu.close();
                return;
            }
        }
        // Backspace on an empty input peels the command flow back one step:
        // clear the selected target (re-open the picker), then the chip.
        if (ev.key === "Backspace" && !this.state.inputText && this.state.activeCommand) {
            ev.preventDefault();
            ev.stopPropagation();
            if (this.state.activeCommand.selection) {
                this.state.activeCommand.selection = null;
                this.openPicker();
            } else {
                this.cancelActiveCommand();
            }
            return;
        }
        // Backspace right next to an inline @ mention pill removes it as one
        // atomic unit — handled explicitly rather than left to each browser's
        // own (inconsistent) contenteditable=false deletion behavior.
        if (ev.key === "Backspace" && !ev.shiftKey && this._deletePillBeforeCaret()) {
            ev.preventDefault();
            this.syncComposerState();
            return;
        }
        if (ev.key === "Enter" && ev.shiftKey) {
            ev.preventDefault();
            this.insertLineBreak();
            return;
        }
        if (ev.key === "Enter" && !ev.shiftKey) {
            ev.preventDefault();
            if (this.state.isTyping) return;
            this.handleSend();
        }
    }

    // -- rich composer (contenteditable) --------------------------------------
    //
    // The composer's DOM is the source of truth while typing — its content is
    // NEVER driven by an Owl-reactive template binding (see the empty
    // <div t-ref="composer"> in chatbot_templates.xml), so Owl's reconciler
    // never touches it and the browser's native caret handling is left
    // completely alone. state.inputText / state.pendingMentions are a
    // READ-ONLY MIRROR recomputed from the DOM after every input — the plain
    // text mirror uses "@[Name]" / "@[Name → Record]" for a pill (see
    // buildMentionPillNode), which is also exactly what gets sent as the
    // message and what ChatUser re-parses back into a pill for display.
    // Only two things ever mutate the DOM directly: inserting a pill
    // (insertPillAtPendingRange) and replacing the whole content
    // (setComposerText, for template fills / drafts / clearing).

    /** Recompute state.inputText and state.pendingMentions from the
     *  composer's actual DOM. Call after ANY change to its content. */
    syncComposerState() {
        const el = this.composerRef.el;
        if (!el) return;
        // Some browsers leave a lone filler <br> behind instead of truly
        // emptying the element (e.g. after backspacing out the last real
        // character) — meaningless filler, not a line break the user typed,
        // but left in place it would mirror as "\n", which is truthy and
        // hides the placeholder even though the box looks empty. Strip it —
        // ONLY when it is the sole child, so an intentional blank line
        // followed by more content is untouched.
        if (el.childNodes.length === 1 && el.firstChild.tagName === "BR") {
            el.removeChild(el.firstChild);
            // The removed node may have been the selection's own anchor —
            // only re-plant the caret if this box is actually focused, so an
            // unrelated caller (e.g. removing a pill elsewhere) can't steal
            // focus/selection as a side effect of this cleanup.
            if (document.activeElement === el) this.placeCaretAtEnd(el);
        }
        let text = "";
        const mentions = [];
        el.childNodes.forEach((node) => {
            if (node.nodeType === Node.TEXT_NODE) {
                text += node.nodeValue;
            } else if (node.tagName === "BR") {
                text += "\n";
            } else if (node.classList?.contains("inline-mention-pill")) {
                const d = node.dataset;
                text += d.recordName ? `@[${d.name} → ${d.recordName}]` : `@[${d.name}]`;
                mentions.push({
                    model: d.model,
                    viewType: d.viewType || null,
                    name: d.name,
                    actionId: d.actionId ? Number(d.actionId) : null,
                    resId: d.resId ? Number(d.resId) : null,
                    recordName: d.recordName || null,
                });
            }
        });
        this.state.inputText = text;
        this.state.pendingMentions = mentions;
    }

    /** String-space length of one composer child node — text nodes count
     *  their own characters, <br> counts as one "\n", a pill counts as the
     *  length of the "@[...]" marker it renders as in the mirror string. */
    _nodeTextLength(node) {
        if (node.nodeType === Node.TEXT_NODE) return node.nodeValue.length;
        if (node.tagName === "BR") return 1;
        if (node.classList?.contains("inline-mention-pill")) {
            const d = node.dataset;
            return (d.recordName ? `@[${d.name} → ${d.recordName}]` : `@[${d.name}]`).length;
        }
        return 0;
    }

    /** Caret position as an offset into the SAME string space syncComposerState
     *  produces — lets the @ trigger regex work against it exactly like it did
     *  against a plain textarea's value/selectionStart. */
    getCaretOffset() {
        const el = this.composerRef.el;
        const sel = window.getSelection();
        if (!el || !sel || !sel.rangeCount) return this.state.inputText.length;
        const range = sel.getRangeAt(0);
        if (!el.contains(range.startContainer)) return this.state.inputText.length;
        if (range.startContainer === el) {
            // Caret sits BETWEEN children — startOffset is a child index here,
            // not a character count.
            let offset = 0;
            for (let i = 0; i < range.startOffset && i < el.childNodes.length; i++) {
                offset += this._nodeTextLength(el.childNodes[i]);
            }
            return offset;
        }
        let offset = 0;
        for (const node of el.childNodes) {
            if (node === range.startContainer) return offset + range.startOffset;
            offset += this._nodeTextLength(node);
        }
        return this.state.inputText.length;
    }

    /** Focus the composer with the caret at the very end. */
    placeCaretAtEnd(el) {
        const range = document.createRange();
        range.selectNodeContents(el);
        range.collapse(false);
        const sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(range);
    }

    placeCaretAfterNode(node) {
        const range = document.createRange();
        range.setStartAfter(node);
        range.collapse(true);
        const sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(range);
    }

    /** Replace the composer's ENTIRE content with plain text — no pills. Used
     *  for slash-command templates, edit-request drafts, quick actions, voice
     *  transcripts, and clearing. Caret goes to the end. */
    setComposerText(text) {
        const el = this.composerRef.el;
        this.state.inputText = text || "";
        this.state.pendingMentions = [];
        if (!el) return;
        el.textContent = text || "";
        requestAnimationFrame(() => {
            el.focus();
            this.placeCaretAtEnd(el);
        });
    }

    /** Focus the composer with the caret at the end, WITHOUT touching its
     *  content (pills and all) — for "just refocus". Use setComposerText to
     *  set new content and focus in one step. */
    focusInput() {
        requestAnimationFrame(() => {
            const el = this.composerRef.el;
            if (!el) return;
            el.focus();
            this.placeCaretAtEnd(el);
        });
    }

    /** Force plain-text paste — a rich-formatted paste (e.g. from a web page)
     *  would otherwise dump arbitrary HTML into the composer, breaking the
     *  {text, <br>, pill} shape syncComposerState/getCaretOffset assume. */
    onComposerPaste(ev) {
        ev.preventDefault();
        const text = (ev.clipboardData || window.clipboardData).getData("text/plain");
        const sel = window.getSelection();
        if (!sel || !sel.rangeCount) return;
        const range = sel.getRangeAt(0);
        range.deleteContents();
        const node = document.createTextNode(text);
        range.insertNode(node);
        this.placeCaretAfterNode(node);
        this.syncComposerState();
    }

    /** Manual Shift+Enter newline, inserted as a lone <br> — left to each
     *  browser's own default, Enter in a contenteditable often wraps
     *  subsequent content in a new block element instead, which would break
     *  the flat {text, <br>, pill} sibling structure this composer assumes. */
    insertLineBreak() {
        const el = this.composerRef.el;
        const sel = window.getSelection();
        if (!el || !sel || !sel.rangeCount) return;
        const range = sel.getRangeAt(0);
        if (!el.contains(range.startContainer)) return;
        range.deleteContents();
        const br = document.createElement("br");
        range.insertNode(br);
        // A lone trailing <br> needs a caret anchor after it to be reachable —
        // an empty text node does that without adding visible content.
        const anchor = document.createTextNode("");
        br.after(anchor);
        this.placeCaretAfterNode(anchor);
        this.syncComposerState();
    }

    /** If the caret sits immediately after a pill span, remove it as one
     *  atomic unit and land the caret exactly where it was — explicit control
     *  instead of relying on each browser's own (inconsistent)
     *  contenteditable=false deletion behavior. Returns whether it fired. */
    _deletePillBeforeCaret() {
        const el = this.composerRef.el;
        const sel = window.getSelection();
        if (!el || !sel || !sel.rangeCount || !sel.isCollapsed) return false;
        const range = sel.getRangeAt(0);
        if (!el.contains(range.startContainer)) return false;
        const node = range.startContainer;
        const offset = range.startOffset;
        let pillNode = null;
        if (node.nodeType === Node.TEXT_NODE && offset === 0) {
            pillNode = node.previousSibling;
        } else if (node === el && offset > 0) {
            pillNode = el.childNodes[offset - 1];
        }
        if (!(pillNode?.nodeType === Node.ELEMENT_NODE
            && pillNode.classList?.contains("inline-mention-pill"))) {
            return false;
        }
        const restoreInText = node.nodeType === Node.TEXT_NODE ? node : null;
        const restoreIndex = node === el ? offset - 1 : null;
        pillNode.remove();
        const r = document.createRange();
        if (restoreInText) {
            r.setStart(restoreInText, 0);
        } else {
            r.setStart(el, Math.max(0, restoreIndex));
        }
        r.collapse(true);
        sel.removeAllRanges();
        sel.addRange(r);
        return true;
    }

    onInput() {
        this.syncComposerState();
        if (this.state.pickerOpen) {
            // typing filters the picker, debounced for the RPC-backed kinds
            const value = this.state.inputText;
            clearTimeout(this._pickerTimer);
            this._pickerTimer = setTimeout(() => this.loadPickerOptions(value), 200);
            return;
        }
        this.updateSlashMenu();
        if (!this.state.slashOpen) {
            this.updateMentionMenu();
        } else {
            this.closeMentionMenu();
        }
    }

    get filteredSlashCommands() {
        const f = this.state.slashFilter;
        const studio = !!this.getUiContext().studio;
        return SLASH_COMMANDS.filter(
            (c) => (!c.studio || studio) &&
                (c.key + " " + c.label).toLowerCase().includes(f)
        );
    }

    /** Open/close/filter the menu from the composer's current mirrored text.
     *  Only a leading "/" on a short first line triggers it; no match closes
     *  it, so Enter falls through to a normal send of the literal text. */
    updateSlashMenu() {
        const text = this.state.inputText;
        const eligible = !this.state.isRecording && !this.state.isTyping &&
            text.startsWith("/") && !text.includes("\n") && text.length <= 30;
        if (!eligible) {
            this.closeSlashMenu();
            return;
        }
        this.state.slashFilter = text.slice(1).toLowerCase();
        const matches = this.filteredSlashCommands;
        this.state.slashOpen = matches.length > 0;
        if (this.state.slashIndex >= matches.length) {
            this.state.slashIndex = 0;
        }
    }

    // -- @ mention menu (attach a screen — model + view — as context) --------

    /** Open/close/filter the @ menu from the caret position (see
     *  getCaretOffset). Triggers when the text right before the caret ends in
     *  "@word", word starting at the beginning of the line or after
     *  whitespace — so, unlike slash commands, this can fire mid-sentence,
     *  not just at the start of the message. */
    updateMentionMenu() {
        const cursor = this.getCaretOffset();
        const head = this.state.inputText.slice(0, cursor);
        const m = head.match(/(?:^|\s)@(\S*)$/);
        if (!m || this.state.isRecording || this.state.isTyping) {
            this.closeMentionMenu();
            return;
        }
        this._mentionStart = cursor - m[1].length - 1;
        this.state.mentionFilter = m[1];
        this.state.mentionOpen = true;
        clearTimeout(this._mentionTimer);
        this._mentionTimer = setTimeout(() => this.loadMentionOptions(m[1]), 200);
    }

    closeMentionMenu() {
        this.state.mentionOpen = false;
        this.state.mentionFilter = "";
        this.state.mentionIndex = 0;
        this.state.mentionOptions = [];
        this.state.mentionLoading = false;
        clearTimeout(this._mentionTimer);
    }

    /** Screens (menu actions) matching the @ filter, each with its model and
     *  default view type — lets the agent be pointed at e.g. "@Accounting
     *  Dashboard" as context even from a completely unrelated screen. Only
     *  actions backed by a real model are offered. */
    async loadMentionOptions(filterText) {
        this.state.mentionLoading = true;
        const domain = [["res_model", "!=", false]];
        if (filterText) domain.push(["name", "ilike", filterText]);
        try {
            // Many menus point at the same model with a different default
            // view (e.g. three separate "Quotations" actions all on
            // sale.order) — the user picks a MODEL to reference, not one
            // specific action, so fetch extra and dedupe down to one entry
            // per model before capping to the visible 8.
            const res = await this.orm.searchRead(
                "ir.actions.act_window", domain, ["name", "view_mode", "res_model"],
                { limit: 30 });
            const seen = new Set();
            this.state.mentionOptions = [];
            for (const r of res) {
                if (seen.has(r.res_model)) continue;
                seen.add(r.res_model);
                this.state.mentionOptions.push({
                    id: r.id,
                    name: r.name,
                    model: r.res_model,
                    viewType: (r.view_mode || "").split(",")[0].trim() || "list",
                });
                if (this.state.mentionOptions.length >= 8) break;
            }
        } catch (e) {
            console.error("mention search failed", e);
            this.state.mentionOptions = [];
        }
        this.state.mentionLoading = false;
        this.state.mentionIndex = 0;
    }

    /** Step one done: insert the pill INLINE immediately, right where "@filter"
     *  sat — no separate "in progress" chip floating above the composer, the
     *  pill itself IS the confirmation. The record picker (step two, optional)
     *  then refines this same pill in place — see pinPillRecord. */
    selectMention(opt) {
        if (!opt) { this.closeMentionMenu(); return; }
        this._mentionFilterLength = this.state.mentionFilter.length;
        this.closeMentionMenu();
        const pill = this.insertPillAtPendingRange({
            model: opt.model, viewType: opt.viewType, name: opt.name, actionId: opt.id,
            resId: null, recordName: null,
        });
        this.openMentionRecordPicker(pill);
    }

    /** Second step of the @ flow: search records on the just-inserted pill's
     *  model, so it can be pinned to one specific record instead of staying a
     *  generic model+view reference. Purely optional — see
     *  skipMentionRecord. The composer is contenteditable=false for the whole
     *  step (see the template) so nothing else can touch the pill meanwhile. */
    openMentionRecordPicker(pillNode) {
        this._pendingPillNode = pillNode;
        this.state.mentionRecordOpen = true;
        this.state.mentionRecordIndex = 0;
        this.loadMentionRecordOptions("");
        requestAnimationFrame(() => this.mentionRecordInput.el?.focus());
    }

    /** Undo step one: pull the pending pill back out, drop a bare "@" in its
     *  place, and reopen the screen menu — lets the user pick a DIFFERENT
     *  model without abandoning the mention outright (the pill's × does
     *  that). The original filter text isn't restored — it was already
     *  consumed to reach this step — so the user just retypes their search. */
    backToMentionMenu() {
        const pill = this._pendingPillNode;
        const el = this.composerRef.el;
        this.closeMentionRecordPicker();   // clears _pendingPillNode — capture first
        if (!pill || !el) return;
        const at = document.createTextNode("@");
        pill.replaceWith(at);
        el.focus();
        this.placeCaretAfterNode(at);
        this.syncComposerState();
        this._mentionStart = this.getCaretOffset() - 1;
        this.state.mentionFilter = "";
        this.state.mentionOpen = true;
        this.loadMentionOptions("");
    }

    closeMentionRecordPicker() {
        this.state.mentionRecordOpen = false;
        this.state.mentionRecordOptions = [];
        this.state.mentionRecordIndex = 0;
        this.state.mentionRecordLoading = false;
        clearTimeout(this._mentionRecordTimer);
        this._pendingPillNode = null;
    }

    onMentionRecordInput(ev) {
        const value = ev.target.value;
        clearTimeout(this._mentionRecordTimer);
        this._mentionRecordTimer = setTimeout(() => this.loadMentionRecordOptions(value), 200);
    }

    /** name_search on the pending pill's model; always offers a leading
     *  "skip" row so a mouse user can pin nothing just as easily as Escape. */
    async loadMentionRecordOptions(filterText) {
        const pill = this._pendingPillNode;
        if (!pill) return;
        const { model, name } = pill.dataset;
        this.state.mentionRecordLoading = true;
        let results = [];
        try {
            const res = await this.orm.call(model, "name_search", [], {
                name: filterText || "", limit: 8,
            });
            results = res.map(([id, resultName]) => ({ id, name: resultName }));
        } catch (e) {
            console.error("mention record search failed", e);
        }
        this.state.mentionRecordOptions = [
            { id: "__skip__", name: `Just "${name}" — no specific record`, skip: true },
            ...results,
        ];
        this.state.mentionRecordLoading = false;
        this.state.mentionRecordIndex = 0;
    }

    selectMentionRecord(opt) {
        if (!opt || opt.skip) {
            this.skipMentionRecord();
            return;
        }
        this._commitMention({ id: opt.id, name: opt.name });
    }

    skipMentionRecord() {
        this._commitMention(null);
    }

    /** Build one inline pill DOM node. NOT Owl-rendered (the composer's
     *  content is fully imperative — see the rich-composer note above
     *  onInput), so its remove (×) button is wired with a real listener
     *  rather than t-on-click. */
    buildMentionPillNode(mention) {
        const span = document.createElement("span");
        span.className = "inline-mention-pill";
        span.contentEditable = "false";
        span.dataset.model = mention.model;
        span.dataset.viewType = mention.viewType || "";
        span.dataset.name = mention.name;
        if (mention.actionId != null) span.dataset.actionId = mention.actionId;

        const icon = document.createElement("i");
        icon.className = "ri-at-line";
        span.appendChild(icon);
        span.appendChild(document.createTextNode(mention.name));
        const remove = document.createElement("i");
        remove.className = "ri-close-line inline-mention-remove";
        remove.title = "Remove";
        remove.addEventListener("click", (ev) => {
            ev.preventDefault();
            ev.stopPropagation();
            // Abandoning a pill whose record picker is still open (step two)
            // must close that picker too, or it's left pointing at a detached
            // node — this is the mention's actual "cancel entirely" now,
            // there's no separate chip/button for it anymore.
            if (this._pendingPillNode === span) this.closeMentionRecordPicker();
            span.remove();
            this.syncComposerState();
            this.focusInput();
        });
        span.appendChild(remove);
        if (mention.recordName) this.pinPillRecord(span, { id: mention.resId, name: mention.recordName });
        return span;
    }

    /** Pin an ALREADY-INSERTED pill to a specific record — adds the "→ Name"
     *  part in place instead of building a new pill, so the one the user
     *  already sees inline is what ends up pinned, not a replacement. */
    pinPillRecord(pillNode, record) {
        pillNode.dataset.resId = record.id;
        pillNode.dataset.recordName = record.name;
        const removeBtn = pillNode.querySelector(".inline-mention-remove");
        const sep = document.createElement("i");
        sep.className = "chip-sep ri-arrow-right-line";
        pillNode.insertBefore(sep, removeBtn);
        pillNode.insertBefore(document.createTextNode(record.name), removeBtn);
    }

    /** Replace the "@filter" text range remembered from step one with a real
     *  pill node, then place the caret right after it. By construction that
     *  range is always inside a single text node — nothing typed since could
     *  have touched it, this runs synchronously right after selectMention. */
    insertPillAtPendingRange(mention) {
        const el = this.composerRef.el;
        if (!el) return null;
        const start = this._mentionStart ?? 0;
        const filterLen = 1 + (this._mentionFilterLength ?? 0); // "@" + filter
        const end = start + filterLen;
        let pos = 0;
        let target = null;
        let targetOffset = 0;
        for (const node of el.childNodes) {
            const len = this._nodeTextLength(node);
            if (node.nodeType === Node.TEXT_NODE && start >= pos && end <= pos + len) {
                target = node;
                targetOffset = start - pos;
                break;
            }
            pos += len;
        }
        const pill = this.buildMentionPillNode(mention);
        if (target) {
            const before = target.nodeValue.slice(0, targetOffset);
            const after = target.nodeValue.slice(targetOffset + filterLen);
            target.nodeValue = before;
            el.insertBefore(pill, target.nextSibling);
            el.insertBefore(document.createTextNode(after), pill.nextSibling);
        } else {
            // Shouldn't happen (see the docstring above) — fail safe rather
            // than silently drop the mention.
            el.appendChild(pill);
        }
        el.focus();
        this.placeCaretAfterNode(pill);
        this.syncComposerState();
        return pill;
    }

    /** Step two done: pin the already-inline pill to `record` ({id, name}),
     *  or leave it exactly as inserted (skip/Escape) — either way the pill
     *  was already visible inline the whole time this step ran. */
    _commitMention(record) {
        const pill = this._pendingPillNode;
        this.closeMentionRecordPicker();   // clears _pendingPillNode — capture first
        if (!pill || !record) { this.focusInput(); return; }
        this.pinPillRecord(pill, record);
        this.syncComposerState();
        this.focusInput();
    }

    closeSlashMenu() {
        this.state.slashOpen = false;
        this.state.slashFilter = "";
        this.state.slashIndex = 0;
    }

    selectSlashCommand(cmd) {
        this.closeSlashMenu();
        if (!cmd) return;
        if (cmd.kind === "local" && cmd.run) {
            cmd.run(this);
            this.setComposerText("");
            return;
        }
        if (cmd.picker) {
            // structured flow: command becomes a chip, picker opens for the target
            this.state.activeCommand = { key: cmd.key, chip: cmd.chip, selection: null };
            this.setComposerText("");
            this.openPicker();
            return;
        }
        this.setComposerText(cmd.template || "");
    }

    /** Edit a pending draft: load its body into the input box for direct editing. */
    onEditRequest(draft) {
        if (draft) {
            this.setComposerText(draft);
        } else {
            this.focusInput();
        }
    }

    // -- structured command flow (chip + target picker) ----------------------

    get activeCommandSpec() {
        const ac = this.state.activeCommand;
        return ac ? SLASH_COMMANDS.find((c) => c.key === ac.key) : null;
    }

    get inputPlaceholder() {
        if (this.state.isRecording) return "";
        const spec = this.activeCommandSpec;
        if (spec) {
            if (this.state.pickerOpen) return spec.picker.placeholder || "Search…";
            if (spec.contentPlaceholder) return spec.contentPlaceholder;
        }
        if (this.state.interrupted) {
            return "Describe the changes you want — or ✓ to proceed, ✕ to cancel";
        }
        return "Hey, ask Cyllo!";
    }

    openPicker() {
        this.state.pickerOpen = true;
        this.state.pickerIndex = 0;
        this.loadPickerOptions("");
    }

    closePicker() {
        this.state.pickerOpen = false;
        this.state.pickerOptions = [];
        this.state.pickerIndex = 0;
        this.state.pickerLoading = false;
        clearTimeout(this._pickerTimer);
    }

    cancelActiveCommand() {
        this.closePicker();
        this.state.activeCommand = null;
        this.setComposerText("");
    }

    async loadPickerOptions(filterText) {
        const spec = this.activeCommandSpec;
        if (!spec || !spec.picker) return;
        if (spec.picker.type === "static") {
            const f = (filterText || "").toLowerCase();
            this.state.pickerOptions = spec.picker.options
                .filter((o) => o.name.toLowerCase().includes(f))
                .slice(0, 10);
            this.state.pickerIndex = 0;
            return;
        }
        // user picker — name_search internal users (share=False) as the user
        if (spec.picker.type === "user") {
            this.state.pickerLoading = true;
            try {
                const res = await this.orm.call("res.users", "name_search", [], {
                    name: filterText || "", args: [["share", "=", false]], limit: 8,
                });
                this.state.pickerOptions = res.map(([id, name]) => ({ id, name }));
            } catch (e) {
                console.error("picker search failed", e);
                this.state.pickerOptions = [];
            }
            this.state.pickerLoading = false;
            this.state.pickerIndex = 0;
            return;
        }
        // partner picker — name_search as the user (access rules apply)
        this.state.pickerLoading = true;
        try {
            const res = await this.orm.call("res.partner", "name_search", [], {
                name: filterText || "", limit: 8,
            });
            this.state.pickerOptions = res.map(([id, name]) => ({ id, name }));
        } catch (e) {
            console.error("picker search failed", e);
            this.state.pickerOptions = [];
        }
        this.state.pickerLoading = false;
        this.state.pickerIndex = 0;
    }

    selectPickerOption(opt) {
        const ac = this.state.activeCommand;
        if (!ac || !opt) return;
        ac.selection = { id: opt.id, name: opt.name };
        this.closePicker();
        this.setComposerText("");
    }

    /** Final message for an active command, or null while incomplete. */
    buildCommandMessage(content) {
        const ac = this.state.activeCommand;
        const spec = this.activeCommandSpec;
        if (!ac || !spec) return content || null;
        if (spec.picker && !ac.selection) {
            this.openPicker();   // target missing — put the user back in the picker
            return null;
        }
        return spec.buildMessage(ac.selection, content);
    }

    /**
     * Prepare the chat for a context affordance so its content doesn't collide
     * with a prior thread. `mode` tags the current thread's purpose; a started-
     * fresh thread archives the old one to history (nothing is lost). Policy:
     *   "always"    -> fresh whenever the thread has messages (the affordance's
     *                  UI lives in the empty state, e.g. the "Generate" offer).
     *   "on-change" -> fresh only when switching INTO this mode; once you're in
     *                  it, keep appending (e.g. exploring many dashboard charts).
     */
    _enterChatContext(mode, policy = "on-change") {
        const hasMessages = this.state.messages.length > 0;
        const needFresh = policy === "always"
            ? hasMessages
            : (this._chatMode !== mode && hasMessages);
        if (needFresh) {
            this.resetChat();
        }
        this._chatMode = mode;
    }

    /** Contextual nudge clicked — open the docked chat (so the host's offer is
     *  visible) and tell the originating module (by key) it was clicked. The
     *  bubble stays as a re-entry affordance until the module clears it. The
     *  nudge may declare a chat mode/policy to start a fresh thread. */
    async onNudgeClick() {
        const nudge = this.state.nudge;
        // Await the maximize before resetting/pushing: otherwise the reset and
        // the host's pushed message (e.g. the dashboard builder) race the open
        // animation, so the empty-state paints first and the pushed content only
        // shows on the next open. Same ordering the EXPLAIN_CHART flow uses.
        await this._maximize_chatbot();
        if (nudge?.mode) {
            this._enterChatContext(nudge.mode, nudge.freshPolicy || "on-change");
        }
        if (nudge) {
            this.env.bus.trigger("CY_AI:NUDGE_CLICKED", { key: nudge.key });
        }
        // If the nudge carries a widget to open (e.g. the dashboard builder),
        // render it HERE — directly, as the final step after the chat is open
        // and the thread is fresh. Doing it in-component (rather than via a
        // host round-trip over the bus) means it can't be lost to the open/reset
        // race, so the builder shows on the FIRST click.
        if (nudge?.widget) {
            this._pushHostMessage({ html: nudge.intro || "", widget: nudge.widget });
        }
    }

    /** Header offer action: start a fresh thread AND run the offer, so one click
     *  visibly replaces the old conversation with fresh results (rather than
     *  resetting to a second, identical-looking offer button). */
    onHeaderSuggest() {
        const offer = this.state.offer;
        if (offer?.mode) {
            this._enterChatContext(offer.mode, offer.freshPolicy || "always");
        } else {
            this.resetChat();
        }
        this.onOfferClick();
    }

    /** Greeting-area offer clicked — ask the host to act (e.g. generate chart
     *  suggestions). The host replies by pushing a message via CY_AI:PUSH_MESSAGE. */
    onOfferClick() {
        const offer = this.state.offer;
        if (offer && !this.state.offerLoading) {
            this.state.offerLoading = true;   // cleared when the host pushes its reply
            this.env.bus.trigger("CY_AI:CHAT_ACTION", { key: offer.key });
        }
    }

    /** Push a host-injected bot message (optionally carrying suggestion cards)
     *  into the current conversation and scroll to it. */
    _pushHostMessage({ html, suggestions, chart, widget } = {}) {
        this.state.offerLoading = false;   // the host has replied — stop the spinner
        const id = "host_" + Date.now() + "_" + Math.random().toString(36).slice(2);
        this.state.messages.push({
            id,
            from: "bot",
            html: html ? markup(html) : markup(""),
            chart_config: null,
            suggestions: suggestions || null,
            chart: chart || null,
            widget: widget || null,
        });
        this.render();
        this.scrollToBottom();
    }

    /**
     * Where the user currently is in the web client — sent with each query as
     * a profile/context HINT (the backend verifies access independently;
     * see core/profiles.py).
     *
     * Primary source is the action service's current controller (authoritative
     * in-memory state; note the current record id lives on controller.props.resId,
     * NOT action.res_id, which stays empty when a form is reached from a list).
     * The URL hash is the fallback for transitions/client actions where the
     * controller is briefly unavailable. Studio mode is a full page reload with
     * ?studio=1, so that flag always comes from the URL.
     */
    getUiContext() {
        try {
            const controller = this.actionService?.currentController;
            const action = controller?.action;
            const props = controller?.props;
            const hash = new URLSearchParams(window.location.hash.slice(1));
            const toInt = (v) => {
                const n = parseInt(v, 10);
                return Number.isFinite(n) && n > 0 ? n : undefined;
            };
            const rawAction = hash.get("action");
            const ctx = {
                action_id: toInt(action?.id) || toInt(rawAction),
                // Client-action tag (e.g. "cy_analytic_sheet"). The action ref in
                // the hash IS the tag for client actions; ignore it when numeric.
                tag: action?.tag || (rawAction && !Number.isFinite(Number(rawAction)) ? rawAction : undefined),
                model: action?.res_model || props?.resModel || hash.get("model") || undefined,
                view_type: controller?.view?.type || hash.get("view_type") || undefined,
                res_id: toInt(props?.resId) || toInt(hash.get("id")),
                studio: new URLSearchParams(window.location.search).get("studio") === "1",
            };
            // strip undefined keys so the payload stays minimal
            Object.keys(ctx).forEach((k) => ctx[k] === undefined && delete ctx[k]);
            return ctx;
        } catch (e) {
            return {};
        }
    }

    /**
     * The ui_context actually sent with a query. When the user has toggled the
     * context chip OFF, the screen/record hints are dropped so the backend's
     * <cyllo_ui_context> block describes nothing. `studio` is kept regardless,
     * since it selects the agent profile (studio vs default), not the record.
     */
    getOutgoingUiContext() {
        const ctx = this.getUiContext();
        const out = this.state.contextEnabled ? ctx : (ctx.studio ? { studio: true } : {});
        // A host screen's explicit payload (e.g. the sheet's fields) is the
        // subject of the request, not an ambient hint, so it rides along even
        // when the context chip is off.
        if (this._hostQueryContext) {
            out.sheet = this._hostQueryContext;
        }
        if (this._hostChartContext) {
            out.chart = this._hostChartContext;
        }
        // The quick-dashboard builder's live state (its cards), so the agent's
        // edit_quick_dashboard tool can reference and change them by id.
        if (this._qdContext) {
            out.quick_dashboard = this._qdContext;
        }
        // The created dashboard on screen (its saved charts), so edit_dashboard
        // can change the live dashboard the user is looking at.
        if (this._dashContext) {
            out.dashboard = this._dashContext;
        }
        // @ mentions are NOT added here — handleSend attaches them, since
        // whether they should ride along depends on typed-vs-programmatic
        // send (same rule as the quote), which this method has no way to know.
        return out;
    }

    /**
     * Recompute the context chip from the current screen. Called on mount, on
     * navigation (hashchange) and when the chat opens. Only the chip DATA is
     * refreshed here — the on/off flag (contextEnabled) is intentionally left
     * untouched so the user's choice persists across navigation.
     */
    /**
     * Whether the current screen is a docking context. Host modules register
     * their contexts in the "cyllo_ai.dock_contexts" registry as either an
     * action-tag / model string, or a `(ctx) => boolean` matcher. Recomputed on
     * every navigation so the docked layout self-corrects (no lifecycle events).
     */
    _isDockContext(ctx) {
        const entries = registry.category("cyllo_ai.dock_contexts").getAll();
        return entries.some((e) => {
            if (typeof e === "function") {
                try { return !!e(ctx); } catch (_) { return false; }
            }
            if (typeof e === "string") return ctx.tag === e || ctx.model === e;
            return false;
        });
    }

    /** Set docked from the current screen (see _isDockContext). */
    _refreshDockState() {
        let ctx;
        try { ctx = this.getUiContext(); } catch (_) { ctx = {}; }
        const docked = this._isDockContext(ctx);
        if (docked !== this.state.docked) {
            this.state.docked = docked;
            this._applyIconStyle();
        }
    }

    async refreshContextChip() {
        this._refreshDockState();
        let ctx;
        try {
            ctx = this.getUiContext();
        } catch (e) {
            this.state.uiContext = null;
            return;
        }
        const model = ctx.model;
        if (!model) { this.state.uiContext = null; return; }
        const controller = this.actionService?.currentController;
        const resId = ctx.res_id || null;
        this.state.uiContext = {
            model,
            modelLabel: controller?.action?.name || model,
            viewType: ctx.view_type || null,
            resId,
            recordName: resId ? `#${resId}` : null,
        };
        if (!resId) return;
        // Resolve a friendly display name (cached per model+id) so the chip
        // reads nicely; fall back to "#id" if the read is denied or fails.
        this._recordNameCache = this._recordNameCache || {};
        const key = `${model}:${resId}`;
        if (this._recordNameCache[key] !== undefined) {
            this.state.uiContext.recordName = this._recordNameCache[key];
            return;
        }
        try {
            const res = await this.orm.read(model, [resId], ["display_name"]);
            const name = (res && res[0] && res[0].display_name) || `#${resId}`;
            this._recordNameCache[key] = name;
            // Apply only if the user is still on the same record.
            const u = this.state.uiContext;
            if (u && u.model === model && u.resId === resId) u.recordName = name;
        } catch (e) {
            this._recordNameCache[key] = `#${resId}`;
        }
    }

    /** Toggle whether the current-screen context is sent with queries. */
    toggleContext() {
        this.state.contextEnabled = !this.state.contextEnabled;
    }

    /** Offer "Reply" when the user selects text inside an assistant response.
     *
     *  The excerpt is captured HERE rather than read back on click: clicking the
     *  button collapses the selection, so by then it would be gone. Coordinates
     *  are viewport-relative because the button is position:fixed. */
    onMessagesMouseUp() {
        const sel = window.getSelection();
        if (!sel || sel.isCollapsed || !sel.rangeCount) {
            this.state.quoteBtn = null;
            return;
        }
        const text = sel.toString().trim();
        const node = sel.anchorNode;
        const el = node && (node.nodeType === 1 ? node : node.parentElement);
        // Only assistant responses are quotable — not the user's own turns.
        if (!text || !el || !el.closest(".chat-bubble.bot")) {
            this.state.quoteBtn = null;
            return;
        }
        const r = sel.getRangeAt(0).getBoundingClientRect();
        this.state.quoteBtn = {
            text: text.length > MAX_QUOTE_CHARS
                ? text.slice(0, MAX_QUOTE_CHARS) + "…" : text,
            x: Math.round(r.left + r.width / 2),
            y: Math.round(r.top),
        };
    }

    /** Commit the offered excerpt as the composer's quoted context. */
    useQuote() {
        if (!this.state.quoteBtn) return;
        this.state.quotedText = this.state.quoteBtn.text;
        this.state.quoteBtn = null;
        window.getSelection()?.removeAllRanges();
        this.focusInput();
    }

    clearQuote() {
        this.state.quotedText = "";
    }

    /** Enter/Space activation for controls that are semantically buttons but
     *  rendered as a div/span (quick actions, the context chip).
     *
     *  stopPropagation() is not optional: onKeyDown is bound on the textarea,
     *  the chatbot-box div AND window, so without it this same keypress would
     *  reach the outer handler and send the message. */
    onActivateKey(ev, fn) {
        if (ev.key === "Enter" || ev.key === " ") {
            ev.preventDefault();
            ev.stopPropagation();
            fn();
        }
    }

    /** Any scroll invalidates the button's position, so dismiss it. */
    onMessagesScroll() {
        if (this.state.quoteBtn) this.state.quoteBtn = null;
    }

    async handleSend(value = null) {
        this.pendingRequestBySession = this.pendingRequestBySession || {};
        this.typingBySession = this.typingBySession || {};
        this.pendingMessagesBySession = this.pendingMessagesBySession || {};
        this.abortBySession = this.abortBySession || {};
        this.generatingBySession = this.generatingBySession || {};

        let text = typeof value === "string" ? value : this.state.inputText.trim();
        if (this.state.activeCommand && typeof value !== "string") {
            const built = this.buildCommandMessage(text);
            if (!built) return; // command incomplete (no target / no content)
            text = built;
            this.closePicker();
            this.state.activeCommand = null;
        }
        if (!text) return;

        // A quoted excerpt travels INSIDE the message rather than as a side
        // channel, so the persisted transcript and a reloaded session read
        // exactly like the live one. Only for typed sends: a programmatic send
        // (quick action, edit-request, host message) must not sweep up a quote
        // the user left sitting in the composer.
        if (typeof value !== "string" && this.state.quotedText) {
            text = `> ${this.state.quotedText.replace(/\s*\n+\s*/g, " ")}\n\n${text}`;
            this.state.quotedText = "";
        }
        this.state.quoteBtn = null;

        // @ mention pills are already INLINE in `text` (they're real tokens
        // in the composer's own content — see insertPillAtPendingRange), so
        // nothing needs baking in here; state.inputText already reads
        // "...@[Contacts → Canonical]..." exactly where it was typed. Only
        // the STRUCTURED side channel for the agent is built here, and only
        // for a typed send — a programmatic one (quick action, edit-request)
        // must not sweep up whatever is still sitting in the composer.
        const __outgoingUiContext = this.getOutgoingUiContext();
        if (typeof value !== "string" && this.state.pendingMentions.length) {
            __outgoingUiContext.mentions = this.state.pendingMentions.map((m) => ({
                model: m.model, view_type: m.viewType, name: m.name, action_id: m.actionId,
                // record_name is NOT sent — the backend re-reads display_name
                // itself (as the requesting user) rather than trust this label.
                res_id: m.resId || undefined,
            }));
        }

        const __sessionId = this.state.session_id;
        const __requestId = (crypto.randomUUID?.() || Math.random().toString(36).slice(2));
        this.pendingRequestBySession[__sessionId] = __requestId;

        // Abort handle so the user can stop generation mid-flight.
        const __abort = new AbortController();
        this.abortBySession[__sessionId] = __abort;
        this.generatingBySession[__sessionId] = true;

        const companyIds = this._getActiveCompanyIds();

        const __tempId = 'pending_' + Date.now() + '_' + Math.random().toString(36).slice(2);
        // A host may attach a chart to this turn (e.g. "explain this chart").
        const pendingMsg = { id: __tempId, from: "user", text, chart: this._nextUserChart || null };
        this._nextUserChart = null;

        this.state.messages.push(pendingMsg);
        this.pendingMessagesBySession[__sessionId] = this.pendingMessagesBySession[__sessionId] || [];
        this.pendingMessagesBySession[__sessionId].push(pendingMsg);

        this.setComposerText("");
        this.closeSlashMenu();
        this.closeMentionMenu();
        this.closeMentionRecordPicker();
        this.typingBySession[__sessionId] = true;
        if (this.state.session_id === __sessionId) {
            this.state.isTyping = true;
            this.state.isGenerating = true;
        }

        this.render();
        this.scrollToBottom();
        try {
            const { userId } = this.user;
            const interrupted = this.state.interrupted;
            const session_id = __sessionId;

            // Live bot message, updated as answer tokens stream in. The activity
            // status (what the agent is doing) is shown separately on the animated
            // loader and cleared the moment answer text starts arriving.
            let liveBot = null;
            let streamBuf = "";
            // Agent trajectory for this turn. tool_start/tool_end used to be
            // collapsed into a transient status string and thrown away; they are
            // the "Worked for Ns · N steps" content, so they are kept here and
            // persisted with the answer.
            const __steps = [];
            const __t0 = Date.now();
            let __workedMs = 0;
            const ensureLiveBot = () => {
                if (!liveBot) {
                    // A temporary id so this message is uniquely keyed for the
                    // whole turn. Without one it renders under t-key=undefined
                    // and collides with any other unkeyed message in the list —
                    // which silently breaks rendering for both. Replaced with the
                    // real record id once the turn is persisted.
                    liveBot = {
                        id: "live_" + Date.now() + "_" + Math.random().toString(36).slice(2),
                        from: "bot", html: markup(""), chart_config: null, interrupted: false,
                        streaming: true, steps: [...__steps], thinkingMs: 0
                    };
                    if (this.state.session_id === __sessionId) {
                        this.state.messages.push(liveBot);
                    }
                }
                return liveBot;
            };
            const setStatus = (label) => {
                if (this.state.session_id === __sessionId) {
                    this.state.activityStatus = label;
                    this.state.isTyping = !!label;
                    this.typingBySession[__sessionId] = !!label;
                    this.render();
                    this.scrollToBottom();
                }
            };
            const renderLive = () => {
                if (this.state.session_id === __sessionId && liveBot) {
                    liveBot.html = markup(this.parseMarkdown(streamBuf.replace(/\\n/g, '\n')));
                    this.render();
                    this.scrollToBottom();
                }
            };
            const { raw, isInterrupted, chartConfig, suggestions, applyEdit, widget, applyQd, applyDash, usage } = await this.streamQuery(
                {
                    text, userId, interrupted, session_id, company_ids: companyIds,
                    ui_context: __outgoingUiContext
                },
                {
                    signal: __abort.signal,
                    onDelta: (chunk) => {
                        ensureLiveBot();
                        // Answer text is arriving — drop the working indicator.
                        if (this.state.session_id === __sessionId) {
                            this.state.activityStatus = "";
                            this.state.isTyping = false;
                            this.typingBySession[__sessionId] = false;
                        }
                        // "Worked for" measures the tool phase — up to the first
                        // answer token. What follows is just streaming prose.
                        if (!__workedMs) __workedMs = Date.now() - __t0;
                        streamBuf += chunk;
                        renderLive();
                    },
                    onActivity: (phase, ev) => {
                        if (phase === "start") {
                            setStatus((ev.label || ev.name) + "…");
                            __steps.push({ name: ev.name, label: ev.label || ev.name, ok: null });
                        } else if (phase === "end") {
                            // Match the most recent still-open step of that name:
                            // one tool can legitimately run more than once a turn.
                            for (let i = __steps.length - 1; i >= 0; i--) {
                                if (__steps[i].name === ev.name && __steps[i].ok === null) {
                                    __steps[i].ok = ev.ok !== false;
                                    break;
                                }
                            }
                            if (ev.ok === false) setStatus((ev.label || ev.name) + " failed");
                        }
                        // Same caveat as the terminal block: liveBot is a plain
                        // object in the reactive array, so this needs a render.
                        // setStatus() supplies one on "start" and on failure,
                        // but a successful "end" would otherwise leave the head
                        // showing the finished step's label.
                        if (liveBot) {
                            liveBot.steps = [...__steps];
                            if (phase === "end" && ev.ok !== false) this.render();
                        }
                    },
                }
            );

            let parsed = null;
            const tryExtractJSON = (s) => {
                if (typeof s !== 'string') return null;
                let t = s.trim();
                t = t.replace(/^`{3}\s*json?\s*/i, '').replace(/`{3}\s*$/i, '').trim();
                t = t.replace(/^`+/, '').replace(/`+$/, '').trim();
                const first = t.indexOf('{');
                const last = t.lastIndexOf('}');
                if (first !== -1 && last !== -1 && last > first) {
                    t = t.slice(first, last + 1);
                }
                try {
                    return JSON.parse(t);
                } catch (_) {
                    return null;
                }
            };

            parsed = tryExtractJSON(raw);
            if (!parsed && typeof raw === 'string') {
                const contentMatch = raw.match(/content=["']([\s\S]*?)["']/);
                if (contentMatch) {
                    parsed = tryExtractJSON(contentMatch[1]);
                }
            }
            if (!parsed && typeof raw === 'string' && raw.includes('{') && raw.includes('}')) {
                const first = raw.indexOf('{');
                const last = raw.lastIndexOf('}');
                if (first !== -1 && last !== -1 && last > first) {
                    try { parsed = JSON.parse(raw.slice(first, last + 1)); } catch (_) { }
                }
            }
            if (!parsed && typeof raw === 'string') {
                try {
                    const once = JSON.parse(raw);
                    if (once && typeof once === 'object' && once.text) {
                        parsed = once;
                    } else if (typeof once === 'string') {
                        try {
                            const twice = JSON.parse(once);
                            if (twice && typeof twice === 'object' && twice.text) {
                                parsed = twice;
                            }
                        } catch (_) { }
                    }
                } catch (_) { }
            }
            if (!parsed && typeof raw === 'string') {
                const m = raw.match(/"text"\s*:\s*"([\s\S]*?)"/);
                if (m) {
                    parsed = { text: m[1] };
                }
            }

            if (!parsed && !this.__loggedParseWarn) {
                this.__loggedParseWarn = true;
            }

            // Finalize the live bot message. Keep the streamed trajectory as the
            // displayed text; attach any chart produced during the turn.
            ensureLiveBot();
            const hasStreamed = !!(streamBuf && streamBuf.trim());
            let cfg = chartConfig || (parsed && parsed.chart_config) || null;
            if (cfg?.series?.[0]?.data?.length === 1) {
                cfg = null;  // a single data point isn't worth charting
            }
            // Skipped when interrupted: `raw` there is the confirm card's own
            // preview markdown (see the "confirm" branch above), not an
            // answer. The card renders those fields itself — falling back to
            // it here would just duplicate the card as a plain paragraph
            // above it when the model said nothing before calling the tool.
            if (!hasStreamed && !isInterrupted) {
                const finalText = (parsed && parsed.text)
                    ? String(parsed.text).replace(/\\n/g, '\n')
                    : (typeof raw === 'string' ? raw.replace(/\\n/g, '\n') : (raw || ''));
                liveBot.html = markup(this.parseMarkdown(finalText));
            }
            liveBot.chart_config = cfg;
            liveBot.suggestions = suggestions || null;
            // A widget the agent chose to render (e.g. the dashboard builder,
            // opened by "create a dashboard") lives in the bot message itself.
            liveBot.widget = widget || null;
            // A direct chart edit ("make it a pie") applies to the host screen.
            if (applyEdit) {
                this.env.bus.trigger("CY_AI:APPLY_EDIT", applyEdit);
            }
            // A patch to the live quick-dashboard builder ("drop the vendor one",
            // "make it a pie") — the active builder widget listens for this.
            if (applyQd) {
                this.env.bus.trigger("CY_AI:QD_PATCH", applyQd);
            }
            // A live (created) dashboard was edited server-side — tell the
            // dashboard screen to reload so the change shows.
            if (applyDash) {
                this.env.bus.trigger("CY_AI:DASH_APPLY", applyDash);
            }
            liveBot.interrupted = isInterrupted;
            liveBot.streaming = false;
            liveBot.usage = usage || null;
            liveBot.steps = [...__steps];
            liveBot.thinkingMs = __workedMs || (Date.now() - __t0);
            liveBot.timestamp = new Date().toISOString();
            // keep the raw markdown on the message: the edit flow extracts the
            // draft body from it (the rendered html is lossy for that)
            liveBot.text = typeof raw === "string" ? raw.replace(/\\n/g, "\n") : "";
            // `liveBot` is a plain object inside the reactive array, so mutating
            // it notifies nothing — every other mutation in this function is
            // paired with an explicit render, and these need one too. Without it
            // the turn stays visually "streaming" (spinner + "Writing answer…")
            // for the whole duration of the persist round-trip below, even
            // though the answer is already fully rendered.
            this.render();

            // --- Persist conversation ---
            // Saving is NOT part of answering. By this point the answer has been
            // produced, rendered and paid for; a storage failure (a migration not
            // applied, a DB blip) must not be reported as a failed turn. Left in
            // the outer try it did exactly that: a red error bubble under a
            // perfectly good answer, and the user's question pushed back into the
            // composer as though it had never been asked.
            let record = null;
            try {
                record = await this.rpc("/chatbot/set_conversation", {
                    user_id: this.user.userId,
                    session_id: session_id || null,
                    user_message: text || null,
                    response_message: isInterrupted ? raw : (parsed?.text ?? raw),
                    chart_config: cfg,
                    user_chart_config: pendingMsg.chart || null,
                    interrupted: isInterrupted,
                    company_ids: companyIds,
                    usage: usage || null,
                    thinking: { ms: liveBot.thinkingMs, steps: __steps },
                });
            } catch (err) {
                // Say so on the turn rather than silently: this exchange really
                // will be gone on reload, and the user should not discover that
                // by losing it.
                console.error("Cyllo AI: answer produced but could not be saved", err);
                liveBot.unsaved = true;
                this.render();
            }

            if (record) {
                liveBot.id = record.id;
                if (record.title && this.state.session_id === __sessionId) {
                    this.state.currentTitle = record.title;
                }
            }

            if (this.pendingMessagesBySession[__sessionId]) {
                this.pendingMessagesBySession[__sessionId] =
                    this.pendingMessagesBySession[__sessionId].filter(m => m.id !== __tempId);
            }

            if (this.pendingRequestBySession[__sessionId] === __requestId && this.state.session_id === __sessionId) {
                this.state.interrupted = isInterrupted;
                this.render();
            }

            if (this.pendingRequestBySession[__sessionId] === __requestId) {
                delete this.pendingRequestBySession[__sessionId];
            }

        } catch (err) {
            console.error('Error in handleSend:', err);
            if (this.state.session_id === __sessionId) {
                // Show the server's actual reason when it gave one. A network
                // failure now arrives as a written sentence ("Cyllo AI can't
                // reach OpenAI…"), which tells the user far more than a generic
                // apology — and tells them it is not a bug in the assistant.
                // Plain string, not markup(), so OWL escapes it.
                // Only errors we authored are shown verbatim. Anything else is a
                // framework/internal message that means nothing to a user, so it
                // gets the plain-English fallback instead — the detail is already
                // in the console line above, where a developer will look.
                const reason = err?.cylloUserFacing ? String(err.message || "").trim() : "";
                this.state.messages.push({
                    // Needs an id like every other message: two consecutive
                    // failures used to push two t-key=undefined messages, and the
                    // second one never rendered.
                    id: "err_" + Date.now() + "_" + Math.random().toString(36).slice(2),
                    from: "bot",
                    html: reason
                        ? `⚠️ ${reason}`
                        : "⚠️ Something went wrong while processing your request.",
                    chart_config: null,
                });
                // The turn was never persisted, so the question would otherwise
                // be lost on reload. Put it back in the composer so retrying is
                // one keystroke — but never clobber something typed since.
                if (!this.state.inputText) {
                    this.setComposerText(text);
                }
            }

            if (this.pendingMessagesBySession[__sessionId]) {
                this.pendingMessagesBySession[__sessionId] =
                    this.pendingMessagesBySession[__sessionId].filter(m => m.id !== __tempId);
            }
        } finally {
            this.typingBySession[__sessionId] = false;
            this.generatingBySession[__sessionId] = false;
            if (this.abortBySession[__sessionId] === __abort) {
                delete this.abortBySession[__sessionId];
            }
            if (this.state.session_id === __sessionId) {
                this.state.isTyping = false;
                this.state.isGenerating = false;
                this.state.activityStatus = "";
                this.render();
            }
        }

        this.env.bus.trigger('LOAD_SIDEBAR', {});
    }

    /** Stop the in-flight generation for the current session. */
    stopGenerating() {
        const sid = this.state.session_id;
        const controller = this.abortBySession?.[sid];
        if (controller) {
            try { controller.abort(); } catch (_) { /* already settled */ }
        }
        // Reflect the stop immediately; handleSend's finally clears the rest.
        if (this.generatingBySession) this.generatingBySession[sid] = false;
        this.state.isGenerating = false;
        this.state.isTyping = false;
        this.state.activityStatus = "";
    }

    // -- text-to-speech (browser SpeechSynthesis) ----------------------------

    /** Read a response aloud. `text` is the cleaned prose from ChatResponse. */
    playMessage(id, text) {
        const synth = window.speechSynthesis;
        if (!synth) { console.warn("speechSynthesis not supported"); return; }
        this.stopSpeaking();                 // single active playback
        const clean = (text || "").trim();
        if (!clean) return;
        this.state.playingMessageId = id;
        // Chrome stops long utterances (~15s); queue sentence-sized chunks so
        // playback runs to the end.
        const chunks = clean.match(/[^.!?。！？\n]+[.!?。！？]?(\s|$)/g) || [clean];
        let cancelled = false;
        this._ttsCancel = () => { cancelled = true; };
        const speakChunk = (i) => {
            if (cancelled || i >= chunks.length) {
                if (!cancelled) this.state.playingMessageId = null;
                return;
            }
            const piece = chunks[i].trim();
            if (!piece) { speakChunk(i + 1); return; }
            const u = new SpeechSynthesisUtterance(piece);
            u.onend = () => speakChunk(i + 1);
            u.onerror = () => { this.state.playingMessageId = null; };
            synth.speak(u);
        };
        speakChunk(0);
    }

    /** Stop any in-progress speech. */
    stopSpeaking() {
        if (this._ttsCancel) { this._ttsCancel(); this._ttsCancel = null; }
        if (window.speechSynthesis) {
            try { window.speechSynthesis.cancel(); } catch (_) { }
        }
        this.state.playingMessageId = null;
    }

    /**
     * Send a query and consume the SSE stream from /chatbot/query/stream.
     * Calls callbacks as events arrive and resolves to { raw, isInterrupted }.
     * Falls back to the non-streaming /chatbot/query endpoint on failure.
     */
    async streamQuery(params, { onDelta, onActivity, signal } = {}) {
        let resp;
        try {
            resp = await fetch("/chatbot/query/stream", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                credentials: "same-origin",
                body: JSON.stringify(params),
                signal,
            });
        } catch (e) {
            // User stopped before the stream opened — don't fall back (that
            // would re-run the whole query); just return empty.
            if (signal?.aborted || e?.name === "AbortError") {
                return {
                    raw: "", isInterrupted: false, chartConfig: null,
                    usage: null, aborted: true
                };
            }
            resp = null;
        }

        if (!resp || !resp.ok || !resp.body) {
            // Fallback: single-shot JSON endpoint.
            const r = await this.rpc("/chatbot/query", params);
            let raw = r.last_message;
            let isInterrupted = false;
            if (r.response !== 'none') { isInterrupted = true; raw = r.response; }
            if (raw) { onDelta?.(raw); }
            return {
                raw, isInterrupted, chartConfig: r.chart_config || null,
                usage: r.usage || null
            };
        }

        const reader = resp.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        let finalText = "";   // final answer (for persistence)
        let isInterrupted = false;
        let chartConfig = null;
        let suggestions = null;   // chart-suggestion cards produced this turn
        let applyEdit = null;     // a direct chart edit to apply this turn
        let widget = null;        // a widget to render in the bot message (e.g. dashboard builder)
        let applyQd = null;       // a patch to the live quick-dashboard builder
        let applyDash = null;     // a live (created) dashboard was edited — reload it
        let usage = null;     // {prompt, completion, total} for the whole turn

        let streamed = "";       // text seen so far (kept if the user stops)
        let aborted = false;
        try {
            // Labelled so the `done` frame can end the read immediately, rather
            // than waiting for the connection to close.
            readLoop:
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                buffer += decoder.decode(value, { stream: true });
                let idx;
                while ((idx = buffer.indexOf("\n\n")) !== -1) {
                    const frame = buffer.slice(0, idx);
                    buffer = buffer.slice(idx + 2);
                    const line = frame.startsWith("data:") ? frame.slice(5).trim() : frame.trim();
                    if (!line) continue;
                    let ev;
                    try { ev = JSON.parse(line); } catch (_) { continue; }
                    if (ev.type === "delta") {
                        streamed += ev.text || "";
                        onDelta?.(ev.text || "");
                    } else if (ev.type === "tool_start") {
                        onActivity?.("start", ev);
                    } else if (ev.type === "tool_end") {
                        onActivity?.("end", ev);
                    } else if (ev.type === "chart") {
                        chartConfig = ev.config || chartConfig;
                    } else if (ev.type === "suggestions") {
                        suggestions = ev.items || suggestions;
                    } else if (ev.type === "apply_edit") {
                        applyEdit = ev.edit || applyEdit;
                    } else if (ev.type === "widget") {
                        widget = ev.widget || widget;
                    } else if (ev.type === "apply_qd") {
                        applyQd = ev.patch || applyQd;
                    } else if (ev.type === "apply_dash") {
                        applyDash = ev.patch || applyDash;
                    } else if (ev.type === "confirm") {
                        isInterrupted = true;
                        finalText = ev.message || "";
                        // Don't fold the confirm-card markdown into the live
                        // narration buffer: the card renders those fields
                        // itself (see ChatResponse#confirmCard). Folding it in
                        // here used to double up the content and, worse, hid
                        // whatever the model said BEFORE the tool call, since
                        // the template shows the card OR the bubble — never
                        // both — so the combined blob just vanished. An empty
                        // nudge still clears the "thinking" status.
                        onDelta?.("");
                    } else if (ev.type === "done") {
                        if (ev.last_message != null) finalText = ev.last_message;
                        if (ev.usage) usage = ev.usage;
                        // The turn is complete — release the connection now.
                        try { await reader.cancel(); } catch (_) { /* already closed */ }
                        break readLoop;
                    } else if (ev.type === "error") {
                        // Flagged as user-facing: the server composes this text for a
                        // person (e.g. "Cyllo AI can't reach OpenAI…"). Errors from
                        // anywhere else carry framework labels like "Cyllo Server
                        // Error", which must never be shown as if they explained
                        // anything — see the catch in handleSend.
                        const streamErr = new Error(ev.message || "stream error");
                        streamErr.cylloUserFacing = true;
                        throw streamErr;
                    }
                }
            }
        } catch (e) {
            // A user stop aborts reader.read(); keep the partial answer.
            if (signal?.aborted || e?.name === "AbortError") {
                aborted = true;
            } else {
                throw e;
            }
        }
        // On a stop with no final answer, persist/return the partial text.
        if (aborted && !finalText) finalText = streamed;
        return {
            raw: finalText, isInterrupted, chartConfig, suggestions, applyEdit,
            widget, applyQd, applyDash, usage, aborted
        };
    }

    resetChat() {
        this.state.messages = [];
        this.setComposerText("");
        this.state.currentTitle = "Cyllo AI";
        this._chatMode = null;   // a manual new chat is a general thread
        const companyIds = this._getActiveCompanyIds();
        const rand = crypto.randomUUID?.() || Math.random().toString(36).slice(2);
        const idsStr = companyIds.length > 0 ? companyIds.sort((a, b) => a - b).join('_') : 'none';
        const newId = `${idsStr}_${rand}`;
        this.state.session_id = newId;
        localStorage.setItem(this._sessionStorageKey(companyIds), newId);
        this.childChartApis = {};
    }

    handleQuickAction = (text) => {
        this.setComposerText(text);
    };

    async onInterruptResponse(event) {
        let messageToUpdate = null
        for (let i = this.state.messages.length - 1; i >= 0; i--) {
            const msg = this.state.messages[i];
            if (msg.from === "bot" && msg.interrupted) {
                messageToUpdate = msg;
                msg.interrupted = false;
                break;
            }
        }
        // Only a persisted record has a numeric id. In-flight messages now carry
        // a temporary string id for rendering purposes, and those must never be
        // handed to orm.write — the turn simply has no history row yet.
        if (messageToUpdate && Number.isInteger(messageToUpdate.id)) {
            await this.orm.write(
                'chatbot.history',
                [messageToUpdate.id],
                { interrupted: false }
            );
        }
        this.handleSend(event);
    }
    async recordVoice() {
        try {
            this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            this.state.isRecording = true
            this.state.recordingStart = Date.now();
            this.state.recordingElapsed = 0;
            this.state.recordingDisplay = "00:00";
            this.recordingTimer = setInterval(() => {
                const seconds = Math.floor((Date.now() - this.state.recordingStart) / 1000);
                this.state.recordingElapsed = seconds;
                const mm = String(Math.floor(seconds / 60)).padStart(2, '0');
                const ss = String(seconds % 60).padStart(2, '0');
                this.state.recordingDisplay = `${mm}:${ss}`;
                this.render();
            }, 1000);
            this.mediaRecorder = new MediaRecorder(this.stream);
            this.audioChunks = [];

            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    this.audioChunks.push(event.data);
                }
            };

            this.mediaRecorder.onstop = async () => {
                this.state.isProcessingVoice = true;
                this.stream.getTracks().forEach(track => track.stop());
                this.state.convertVoice = true
                // Use the format the recorder actually produced (webm on
                // Chrome/Firefox, mp4 on Safari) so the backend can label it
                // correctly for transcription.
                const recMime = ((this.mediaRecorder && this.mediaRecorder.mimeType)
                    || 'audio/webm').split(';')[0].trim() || 'audio/webm';
                const recordedBlob = new Blob(this.audioChunks, { type: recMime });
                // Transcode to WAV in-browser (no library): gpt-4o-transcribe
                // rejects webm/opus, and WAV is accepted by OpenAI + Gemini.
                // Fall back to the original recording if decoding fails.
                let sendBlob = recordedBlob;
                let sendMime = recMime;
                try {
                    sendBlob = await this._audioBlobToWav(recordedBlob);
                    sendMime = 'audio/wav';
                } catch (e) {
                    console.error('audio → WAV conversion failed; sending original', e);
                }
                const encoded_audio = await this.blobToBase64(sendBlob);
                const audioConvertion = await this.rpc("/cyllo/speech_to_text", {
                    encoded_audio: encoded_audio,
                    mime: sendMime,
                });
                this.state.convertVoice = false
                this.state.isProcessingVoice = false
                this.setComposerText(audioConvertion);
            };
            this.mediaRecorder.start();
        } catch (err) {
            console.error('Error recording audio:', err);
        }
    }

    async stopRecording() {
        if (this.state.isRecording && this.mediaRecorder) {
            this.mediaRecorder.stop();
            this.state.isRecording = false;
            if (this.recordingTimer) {
                clearInterval(this.recordingTimer);
                this.recordingTimer = null;
            }
        }
    }
    blobToBase64(blob) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onloadend = () => {
                const base64String = reader.result.split(',')[1];
                resolve(base64String);
            };
            reader.onerror = reject;
            reader.readAsDataURL(blob);
        });
    }

    /**
     * Transcode a recorded audio blob (webm/opus on Chrome/Firefox, mp4 on
     * Safari) to a mono 16-bit PCM WAV, using only the browser's Web Audio API
     * (no library). gpt-4o-transcribe rejects webm/opus; WAV is accepted by
     * both OpenAI and Gemini.
     */
    async _audioBlobToWav(blob) {
        const arrayBuffer = await blob.arrayBuffer();
        const AudioCtx = window.AudioContext || window.webkitAudioContext;
        const ctx = new AudioCtx();
        try {
            const audioBuffer = await ctx.decodeAudioData(arrayBuffer);
            return this._encodeWav(audioBuffer);
        } finally {
            ctx.close();
        }
    }

    /** Encode an AudioBuffer as a mono 16-bit PCM WAV Blob. */
    _encodeWav(audioBuffer) {
        const length = audioBuffer.length;
        const sampleRate = audioBuffer.sampleRate;
        const numCh = audioBuffer.numberOfChannels;
        // Downmix to mono — smaller payload, and fine for speech.
        const mono = new Float32Array(length);
        for (let ch = 0; ch < numCh; ch++) {
            const data = audioBuffer.getChannelData(ch);
            for (let i = 0; i < length; i++) mono[i] += data[i] / numCh;
        }
        const dataSize = length * 2;            // 16-bit samples
        const buffer = new ArrayBuffer(44 + dataSize);
        const view = new DataView(buffer);
        const writeStr = (off, s) => {
            for (let i = 0; i < s.length; i++) view.setUint8(off + i, s.charCodeAt(i));
        };
        writeStr(0, "RIFF");
        view.setUint32(4, 36 + dataSize, true);
        writeStr(8, "WAVE");
        writeStr(12, "fmt ");
        view.setUint32(16, 16, true);           // fmt chunk size
        view.setUint16(20, 1, true);            // PCM
        view.setUint16(22, 1, true);            // mono
        view.setUint32(24, sampleRate, true);
        view.setUint32(28, sampleRate * 2, true); // byte rate
        view.setUint16(32, 2, true);            // block align
        view.setUint16(34, 16, true);           // bits per sample
        writeStr(36, "data");
        view.setUint32(40, dataSize, true);
        let off = 44;
        for (let i = 0; i < length; i++) {
            const s = Math.max(-1, Math.min(1, mono[i]));
            view.setInt16(off, s < 0 ? s * 0x8000 : s * 0x7fff, true);
            off += 2;
        }
        return new Blob([view], { type: "audio/wav" });
    }
    cancelRecording() {
        if (this.state.isRecording && this.mediaRecorder) {
            this.mediaRecorder.ondataavailable = null;
            this.mediaRecorder.onstop = null;

            if (this.mediaRecorder.state !== 'inactive') {
                this.mediaRecorder.stop();
            }
            if (this.stream) {
                this.stream.getTracks().forEach(track => track.stop());
            }
            this.audioChunks = [];
            this.state.isRecording = false;
            if (this.recordingTimer) {
                clearInterval(this.recordingTimer);
                this.recordingTimer = null;
            }
            this.state.recordingStart = 0;
            this.state.recordingElapsed = 0;
            this.state.recordingDisplay = "00:00";
            this.mediaRecorder = null;
            this.stream = null;
        }
    }

    async loadSession(sessionId) {
        const companyIds = this._getActiveCompanyIds();
        const history = await this.rpc("/chatbot/get_conversation", {
            session_id: sessionId,
            company_ids: companyIds
        });

        this.state.session_id = sessionId;
        localStorage.setItem(this._sessionStorageKey(companyIds), sessionId);

        // ADDED 'index' argument here
        this.state.messages = (history || []).map((msg, index) => {

            // ADDED Safe ID Generation (crucial for t-key="msg.id")
            // If msg.id is null, we create a unique one using the session + index
            const safeId = msg.id
                ? msg.id
                : `${sessionId}_temp_${msg.timestamp || Date.now()}_${index}`;

            let htmlContent = "";
            if (msg.from === "bot") {
                // See the identical guard (and CONFIRM_CARD_RE) in the
                // onWillStart history mapping: a confirm-card turn's `text`
                // is the card's own preview markdown, not narration — checked
                // by shape, not by `msg.interrupted`, since that resolves to
                // false once handled while the card keeps rendering anyway.
                htmlContent = (msg.text && !CONFIRM_CARD_RE.test(msg.text))
                    ? markup(this.parseMarkdown(msg.text))
                    : (msg.html || "");
            } else {
                // Same as the history mapping in onWillStart: the user's text is
                // not markdown. See the note there.
                htmlContent = msg.html || "";
            }
            return {
                id: safeId, //  Use the safeId
                from: msg.from,
                html: htmlContent,
                text: msg.text,
                chart_config: msg.chart_config || null,
                chart: msg.chart || null,
                interrupted: msg.interrupted,
                timestamp: msg.timestamp,
                usage: msg.usage || null,
                steps: msg.thinking?.steps || null,
                thinkingMs: msg.thinking?.ms || 0,
            };
        });

        const pending = this.pendingMessagesBySession?.[sessionId] || [];
        if (pending.length) {
            this.state.messages = [...this.state.messages, ...pending];
        }
        this.state.isTyping = !!this.typingBySession?.[sessionId];
        this.state.isGenerating = !!this.generatingBySession?.[sessionId];
        this.scrollToBottom();
    }

    onSelectSession = (s) => {
        if (s && s.session_id) {
            this.state.currentTitle = s.title || "Cyllo AI";
            this.loadSession(s.session_id);
            this.state.historyOpen = false;
            this._maximize_chatbot();
        }
    };

    toggleHistory() {
        this.state.historyOpen = !this.state.historyOpen;
    }

}
ChatBot.template = "ChatBot";
ChatBot.components = {
    ChatUser,
    ChatResponse,
    ChatSidebar,
};

// Mount the chatbot at the WebClient root instead of inside the navbar systray.
// The systray is hidden on full-canvas screens (dashboard, barcode, workflow),
// which took the assistant down with it. As a main component it stays available
// everywhere the backend is loaded, independent of navbar visibility. The
// component self-gates its display via config (cyllo_ai_widget), so it needs no props.
registry.category("main_components").add("cyllo_ai.ChatBot", {
    Component: ChatBot,
});