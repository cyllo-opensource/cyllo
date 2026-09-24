/** @odoo-module **/
import { onMounted, onWillUnmount, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { ChatBot } from "../chatbot/chatbot";

export class ChatBotScreen extends ChatBot {
    static props = {
        action: { type: Object, optional: true },
        actionId: { type: [Number, String], optional: true },
        className: { type: String, optional: true },
    };

    // Holds a session_id fired by the bubble's openInScreen() just before
    // selectMenu() triggers a navigation. Consumed once in onWillStart.
    static _pendingSessionId = null;

    setup() {
        super.setup(...arguments);
        // Always open and never minimised in screen mode.
        this.state.chatOn = true;
        this.state.minimized = false;
        // Session-row "..." menu (edit/delete) — mirrors ChatSidebar's, which
        // the docked overlay has but this always-visible screen sidebar never
        // got when it was built.
        Object.assign(this.state, { activeSubMenu: null, activeRenameTextbox: null });

        onWillStart(async () => {
            await this.loadRecentSessions();
            // Restore session passed from the bubble via openInScreen().
            // Two paths: selectMenu (bus event stored in _pendingSessionId)
            // or doAction (action context cy_ai_session_id).
            const fromBus = ChatBotScreen._pendingSessionId;
            const fromCtx = this.props.action?.context?.cy_ai_session_id;
            const passedSessionId = fromBus || fromCtx;
            ChatBotScreen._pendingSessionId = null;  // consume immediately
            if (passedSessionId && passedSessionId !== this.state.session_id) {
                await this.loadSession(passedSessionId);
            }
        });

        // Hide the global floating bubble (ChatBot main_component) while this
        // screen is mounted, and restore it when the user navigates away.
        onMounted(() => this.env.bus.trigger("CY_AI:HIDE_BUBBLE"));
        onWillUnmount(() => this.env.bus.trigger("CY_AI:SHOW_BUBBLE"));
    }

    async loadRecentSessions() {
        try {
            const companyIds = this._getActiveCompanyIds();
            const sessions = await this.orm.call(
                'chatbot.history',
                'get_user_sessions',
                [companyIds]
            );
            this.state.sessions = sessions || [];
        } catch (e) {
            console.error('Failed to load recent sessions:', e);
            this.state.sessions = [];
        }
    }

    showSubMenu(ev, session) {
        ev.stopPropagation();
        this.state.activeSubMenu = this.state.activeSubMenu === session.session_id ? null : session.session_id;
    }

    async deleteSession(ev, session) {
        ev.stopPropagation();
        ev.preventDefault();
        try {
            const companyIds = this._getActiveCompanyIds();
            await this.orm.call('chatbot.history', 'delete_session', [session.session_id, companyIds]);
            this.state.sessions = this.state.sessions.filter((s) => s.session_id !== session.session_id);
            this.state.activeSubMenu = null;
        } catch (error) {
            console.error('Failed to delete session:', error);
        }
    }

    async editSessionTitle(session) {
        const inputEl = document.getElementById('input-session-' + session.session_id);
        if (!inputEl) return;
        const newTitle = inputEl.value;
        try {
            await this.orm.call('chatbot.history', 'rename_session', [], {
                session_id: session.session_id,
                new_title: newTitle,
            });
            const sessionObj = this.state.sessions.find((s) => s.session_id === session.session_id);
            if (sessionObj) sessionObj.title = newTitle;
            this.state.activeSubMenu = null;
            this.state.activeRenameTextbox = null;
        } catch (error) {
            console.error('Failed to edit session title:', error);
        }
    }

    toggleRenameTextbox(session) {
        this.state.activeRenameTextbox = this.state.activeRenameTextbox === session.session_id ? null : session.session_id;
        this.state.activeSubMenu = null;
    }

    async resetChat() {
        await super.resetChat(...arguments);
        await this.loadRecentSessions();
    }

    async handleSend() {
        await super.handleSend(...arguments);
        await this.loadRecentSessions();
    }
}

ChatBotScreen.template = "ChatBotScreen";
ChatBotScreen.components = { ...ChatBot.components };

registry.category("actions").add("cyllo_ai.ChatBotScreen", ChatBotScreen);

// The bubble's openInScreen() triggers CY_AI:OPEN_SESSION on env.bus before
// calling selectMenu(). env.bus is an EventBus that also dispatches a native
// CustomEvent on the document with the same name — capture it here at module
// level so _pendingSessionId is set before onWillStart runs.
document.addEventListener("CY_AI:OPEN_SESSION", (ev) => {
    ChatBotScreen._pendingSessionId = ev.detail || null;
});
