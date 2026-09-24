/** @odoo-module **/
import { Component, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { connectAccountPlatforms } from "./platform_registry";

export class ConnectAccountDialog extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({ values: {} });
    }

    get entry() {
        return connectAccountPlatforms.get(this.props.platform, false);
    }

    get title() {
        return `Connect ${this.entry?.title || ""}`;
    }

    async connect() {
        const entry = this.entry;
        if (!entry || !entry.connect) {
            return;
        }
        try {
            await entry.connect(this, this.state.values);
        } catch (error) {
            return false;
        }
    }
}
ConnectAccountDialog.template = "cyllo_social_media_marketing.ConnectAccountDialog";
ConnectAccountDialog.components = { Dialog };
ConnectAccountDialog.props = {
    close: { type: Function, optional: true },
    platform: { type: String },
    onConnected: { type: Function },
};
