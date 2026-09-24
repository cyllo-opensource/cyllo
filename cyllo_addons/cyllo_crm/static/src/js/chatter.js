/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { Chatter } from "@mail/core/web/chatter";
import { useService } from "@web/core/utils/hooks";
import { onMounted, onWillUpdateProps } from "@odoo/owl";
import { MessageCardList } from "@mail/core/common/message_card_list";

patch(Chatter.prototype, {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.state.showPinnedMessages ??= false;

        onMounted(() => this._loadPinnedMessages());
        onWillUpdateProps((nextProps) => {
            if (
                this.props.threadId !== nextProps.threadId ||
                this.props.threadModel !== nextProps.threadModel
            ) {
                this.state.showPinnedMessages = false;
                this._loadPinnedMessages();
            }
        });
    },

    /**
     * Load pinned messages from database and sync with thread messages
     */
    async _loadPinnedMessages() {
        // Wait for thread to be ready
        if (!this.state.thread?.id || !this.props.threadModel || !this.props.threadId) {
            return;
        }

        // Small delay to ensure messages are loaded
        await new Promise(resolve => setTimeout(resolve, 100));

        try {
            // Fetch pinned message IDs from database
            const pinnedRecords = await this.orm.searchRead(
                "mail.message",
                [
                    ["is_pinned", "=", true],
                    ["model", "=", this.props.threadModel],
                    ["res_id", "=", this.props.threadId]
                ],
                ["id"]
            );

            const pinnedIds = new Set(pinnedRecords.map(r => r.id));

            // Sync pinned state with thread messages
            if (this.state.thread.messages) {
                for (const msg of this.state.thread.messages) {
                    msg.is_pinned = pinnedIds.has(msg.id);
                }
            }
        } catch (error) {
            console.error("Error loading pinned messages:", error);
        }
    },

    get pinnedMessages() {
        if (!this.state.thread?.messages) {
            return [];
        }
        return this.state.thread.messages.filter((m) => m.is_pinned === true);
    },

    togglePinnedMessages() {
        this.state.showPinnedMessages = !this.state.showPinnedMessages;
    },
});

Chatter.components = { ...Chatter.components, MessageCardList };