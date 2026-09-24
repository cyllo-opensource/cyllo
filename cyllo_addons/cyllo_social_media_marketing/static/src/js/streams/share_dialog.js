/** @odoo-module **/
import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";

export class ShareDialog extends Component {
    static template = "cyllo_social_media_marketing.ShareDialog";
    static components = { Dialog };
    static props = {
        close: { type: Function, optional: true },
        text: { type: String, optional: true },
        permalink: { type: String, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.user = useService("user");
        this.state = useState({ query: "", users: [] });
        this.searchUsers();
    }

    async searchUsers() {
        const domain = [["share", "=", false], ["id", "!=", this.user.userId]];
        if (this.state.query) {
            domain.push(["name", "ilike", this.state.query]);
        }
        this.state.users = await this.orm.searchRead("res.users", domain, ["id", "name"], { limit: 24 });
    }

    onSearchInput(ev) {
        this.state.query = ev.target.value;
        this.searchUsers();
    }

    avatarUrl(userId) {
        return `/web/image?model=res.users&id=${userId}&field=avatar_128`;
    }

    async copyLink() {
        try {
            await navigator.clipboard.writeText(this.props.permalink || "");
            this.notification.add("Link copied.", { type: "success" });
        } catch {
            this.notification.add("Could not copy the link.", { type: "danger" });
        }
    }

    async sendToUser(targetUser) {
        const res = await this.orm.call("social.media.post", "share_post_to_discuss", [], {
            user_id: targetUser.id,
            text: this.props.text || "",
            permalink: this.props.permalink || "",
        });
        if (res && res.type === "ir.actions.client") {
            this.notification.add(res.params.message, { type: "danger" });
            return;
        }
        this.notification.add(`Sent to ${targetUser.name}.`, { type: "success" });
        this.props.close();
    }
}
