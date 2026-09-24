/** @odoo-module **/
import {
    connectAccountPlatforms,
    validateRequiredFields,
} from "@cyllo_social_media_marketing/js/platform_registry";

const youtubeFields = [
    { key: "name", label: "Channel Name", type: "text", required: true, placeholder: "Enter YouTube Channel Name" },
    { key: "client_number", label: "Client Id", type: "text", required: true, placeholder: "Enter Client ID" },
    { key: "client_secret", label: "Client Secret", type: "text", required: true, placeholder: "Enter Client Secret" },
];



connectAccountPlatforms.add("youtube.account", {
    ...connectAccountPlatforms.get("youtube.account", {}),
    fields: youtubeFields,
    async connect(comp, values) {
        const message = validateRequiredFields(youtubeFields, values);
        if (message) {
            comp.action.doAction({
                type: "ir.actions.client",
                tag: "display_notification",
                params: { message, type: "warning" },
            });
        }
        const result = await comp.orm.call("social.media.post", "action_create_connect", ["", { ...values }, "youtube.account"], {});
        comp.props.close();
        if (result) {
            comp.action.doAction({
                type: "ir.actions.act_window",
                res_model: "youtube.account",
                res_id: result,
                views: [[false, "form"]],
                target: "current",
            });
        }
    },
}, { force: true });
