/** @odoo-module **/
import { AttachmentView } from "@mail/core/common/attachment_view";
import { patch } from "@web/core/utils/patch";

AttachmentView.props = ["threadId?", "threadModel"];

patch(AttachmentView.prototype, {
    get currentAttachments() {
        return this.state.thread?.attachmentsInWebClientView || [];
    },

    getCurrentIndex() {
        const attachments = this.currentAttachments;
        if (!attachments.length) {
            return 0;
        }
        const currentAttachment = this.state.thread?.mainAttachment;
        if (!currentAttachment) {
            return 0;
        }
        // Match by id first for reliability
        let index = attachments.findIndex((att) => att.id === currentAttachment.id);
        // Fallback to .eq() if needed
        if (index === -1 && typeof currentAttachment.eq === "function") {
            index = attachments.findIndex((att) => att.eq(currentAttachment));
        }
        return index === -1 ? 0 : index;
    },

    async setAttachmentIndex(index) {
        const attachments = this.currentAttachments;
        if (!attachments.length) {
            return;
        }
        const safeIndex = ((index % attachments.length) + attachments.length) % attachments.length;
        const targetAttachment = attachments[safeIndex];
        if (this.state.thread && targetAttachment) {
            this.state.thread.mainAttachment = targetAttachment;
        }
        // Force immediate component re-render so image src and title update in the DOM
        this.render();

        // Safely persist to backend without blocking UI or crashing on locked/posted invoices
        try {
            if (this.env?.services?.orm && targetAttachment?.id) {
                await this.env.services.orm.call("ir.attachment", "register_as_main_attachment", [
                    targetAttachment.id,
                ]);
            }
        } catch (error) {
            console.warn("Could not register main attachment on server:", error);
        }
    },

    onClickNext() {
        const attachments = this.currentAttachments;
        if (attachments.length <= 1) {
            return;
        }
        const currentIndex = this.getCurrentIndex();
        this.setAttachmentIndex(currentIndex + 1);
    },

    onClickPrevious() {
        const attachments = this.currentAttachments;
        if (attachments.length <= 1) {
            return;
        }
        const currentIndex = this.getCurrentIndex();
        this.setAttachmentIndex(currentIndex - 1);
    },

    get displayName() {
        const main = this.state.thread?.mainAttachment;
        return main?.filename || main?.name || super.displayName || "";
    },
});