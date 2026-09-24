/** @odoo-module */
import { Chatter } from "@mail/core/web/chatter";
import { patch } from "@web/core/utils/patch";

patch(Chatter.prototype, {
    async sendWhatsapp() {
        await new Promise((resolve) => {
            this.env.services.action.doActionButton({
                type: "object",
                resId: this.props.threadId,
                name: "action_default_template",
                resModel: "whatsapp.template.message",
                context: {
                    active_id: this.props.threadId,
                    model: this.props.threadModel
                },
            });
        });
    },
});