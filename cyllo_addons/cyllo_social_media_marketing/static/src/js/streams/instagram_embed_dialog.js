/** @odoo-module **/
import { Component } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

export class InstagramEmbedDialog extends Component {
    get embedUrl() {
        const permalink = this.props.permalink || "";
        return permalink.endsWith("/") ? `${permalink}embed` : `${permalink}/embed`;
    }
}
InstagramEmbedDialog.template = "cyllo_social_media_marketing.InstagramEmbedDialog";
InstagramEmbedDialog.components = { Dialog };
InstagramEmbedDialog.props = {
    close: { type: Function, optional: true },
    permalink: { type: String },
};
