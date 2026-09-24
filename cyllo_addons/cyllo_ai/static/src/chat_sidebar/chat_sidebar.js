/** @odoo-module **/
import { Component, useState, onMounted, onWillUnmount, onWillRender, onWillStart, useRef } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class ChatSidebar extends Component {
    static props = {
        onClose: { type: Function, optional: true },
        onSelect: { type: Function, optional: true },
    };
    setup() {
        // services
        this.orm = useService('orm');
        this.user = useService('user');
        this.company = useService('company');

        // ui state
        this.state = useState({
            sessions: [],
            loading: true,
            activeSubMenu: null,
            activeRenameTextbox: null,
            closing: false,
            editSessionTitle: false,
        });

        // layout
        this.width = 300; // px
        this.gap = 0;
        this.root = useRef('root');

        // Track active company IDs for change detection
        this.lastActiveCompanyIds = this._getActiveCompanyIds();

        onWillStart(async () => {
            await this._loadSessions();
        });

        onMounted(() => {
            window.addEventListener('resize', this._onResize);
            const el = this.root?.el;
            requestAnimationFrame(() => {
                el.classList.add("ready");
            });
        });
        onWillUnmount(() => {
            window.removeEventListener('resize', this._onResize);
        });

        onWillRender(() => {
            // Check if active company selection has changed
            const currentActiveIds = this._getActiveCompanyIds();
            if (!this._areCompanyIdsEqual(currentActiveIds, this.lastActiveCompanyIds)) {
                this.lastActiveCompanyIds = currentActiveIds;
                this._loadSessions();
            }
        });

        this.env.bus.addEventListener("LOAD_SIDEBAR", ({ detail }) => {
            this._loadSessions();
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

    async _loadSessions() {
        this.state.loading = true;

        try {
            const companyIds = this._getActiveCompanyIds();
            // Simple backend call - let Python do the work
            const sessions = await this.orm.call(
                'chatbot.history',
                'get_user_sessions',
                [companyIds]
            );

            this.state.sessions = sessions;

        } catch (e) {
            console.error('Failed to load chat sessions:', e);
            this.state.sessions = [];
        } finally {
            this.state.loading = false;
        }
    }
    showSubMenu(ev, session) {
        ev.stopPropagation();
        // Toggle the submenu - if clicking the same session, close it; otherwise, open for the new session
        this.state.activeSubMenu = this.state.activeSubMenu === session.session_id ? null : session.session_id;
    }
    async deleteSession(ev, session) {
        ev.stopPropagation();
        ev.preventDefault();  // Prevent any default behavior

        try {
            const companyIds = this._getActiveCompanyIds();

            // Call the backend to delete the session
            await this.orm.call(
                'chatbot.history',
                'delete_session',
                [session.session_id, companyIds]  // Pass company_ids for proper deletion
            );

            // Update the UI by removing the deleted session
            this.state.sessions = this.state.sessions.filter(
                (s) => s.session_id !== session.session_id
            );

            // Close the submenu
            this.state.activeSubMenu = null;

        } catch (error) {
            console.error('Failed to delete session:', error);
            // Optionally show an error message to the user
        }
    }
    async editSessionTitle(session) {
        const inputEl = document.getElementById('input-session-' + session.session_id);
        if (!inputEl) return
        const newTitle = inputEl.value; // Get the text written inside
        try {
            // Call the backend to delete the session
            await this.orm.call(
                'chatbot.history',
                'rename_session',
                [], // Positional args (empty)
                {   // Keyword args (explicit names)
                    session_id: session.session_id,
                    new_title: newTitle
                }
            );

            // Update the UI by removing the deleted session
            const sessionObj = this.state.sessions.find(s => s.session_id === session.session_id);
            if (sessionObj) {
                sessionObj.title = newTitle;
            }

            // Close the submenu
            this.state.activeSubMenu = null;
            this.state.activeRenameTextbox = null;
        } catch (error) {
            console.error('Failed to edited session title:', error);
        }
    }

    selectSession(s) {
        if (this.props && typeof this.props.onSelect === 'function') {
            this.props.onSelect(s);
        }
    }

    toggleRenameTextbox(session) {
        this.state.activeRenameTextbox = this.state.activeRenameTextbox === session.session_id ? null : session.session_id;
        this.state.activeSubMenu = null;
        // 3. (Optional) If you really want to use the boolean:
        this.state.editSessionTitle = !this.state.editSessionTitle;
    }
    chatSideBarClose() {
        this.state.closing = true

        setTimeout(() => {
            this.props.onClose?.();  // notify parent AFTER animation
        }, 200);
    }
    _onResize = () => {
        this.render();
    }
}

ChatSidebar.template = "ChatSidebar";
