/** @odoo-module **/
import { registry } from "@web/core/registry";


export const connectAccountPlatforms = registry.category("social_connect_account_platforms");


export function validateRequiredFields(fields, values) {
    for (const field of fields) {
        if (field.required && !values[field.key]) {
            return `${field.label} is required`;
        }
    }
    return null;
}

function notifyWarning(comp, message) {
    comp.action.doAction({
        type: "ir.actions.client",
        tag: "display_notification",
        params: { message, type: "warning" },
    });
}


async function createAndConnect(comp, data, platform) {
    const result = await comp.orm.call("social.media.post", "action_create_connect", ["", data, platform], {});
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
}

const fbFields = [
    { key: "facebook_page_name", label: "Page Name", type: "text", required: true, placeholder: "Enter Facebook Page Name" },
    { key: "facebook_access_token", label: "Page Access Token", type: "text", required: true, placeholder: "Enter Page Access Token" },
    { key: "facebook_user_access_token", label: "User Access Token", type: "text", required: true, placeholder: "Enter User Access Token" },
    { key: "meta_app_number", label: "Meta App Number", type: "text", required: true, placeholder: "Enter Meta App Number" },
    { key: "meta_app_secret", label: "Meta App Secret", type: "text", required: true, placeholder: "Enter Meta App Secret" },
];

connectAccountPlatforms.add("social.fb.account", {
    title: "Facebook Account",
    icon: "fa fa-facebook",
    color: "#1877f2",
    moduleName: "cyllo_facebook",
    moduleLabel: "Facebook",
    fields: fbFields,
    async connect(comp, values) {
        const message = validateRequiredFields(fbFields, values);
        if (message) {
            notifyWarning(comp, message);
        }
        await createAndConnect(comp, { ...values }, "social.fb.account");
    },
});

const igFields = [
    { key: "facebook_insta_page_name", label: "Page Name", type: "text", required: true, placeholder: "Enter Instagram Page Name" },
    { key: "instagram_access_token", label: "User Access Token", type: "text", required: true, placeholder: "Enter User Access Token" },
    { key: "instagram_page_access_token", label: "Page Access Token", type: "text", required: true, placeholder: "Enter Page Access Token" },
    { key: "meta_app_number", label: "Meta App Number", type: "text", required: true, placeholder: "Enter Meta App Number" },
    { key: "meta_app_secret", label: "Meta App Secret", type: "text", required: true, placeholder: "Enter Meta App Secret" },
];

connectAccountPlatforms.add("social.insta.account", {
    title: "Instagram Account",
    icon: "fa fa-instagram",
    color: "#c13584",
    moduleName: "cyllo_instagram",
    moduleLabel: "Instagram",
    fields: igFields,
    async connect(comp, values) {
        const message = validateRequiredFields(igFields, values);
        if (message) {
            notifyWarning(comp, message);
        }
        await createAndConnect(comp, { ...values }, "social.insta.account");
    },
});




connectAccountPlatforms.add("youtube.account", {
    title: "YouTube Account",
    icon: "fa fa-youtube-play",
    color: "#ff0000",
    moduleName: "cyllo_youtube",
    moduleLabel: "YouTube",
    fields: [],
    connect: null,
});

connectAccountPlatforms.add("linkedin.account", {
    title: "LinkedIn Account",
    icon: "fa fa-linkedin",
    color: "#0a66c2",
    moduleName: "cyllo_linkedin",
    moduleLabel: "LinkedIn",
    fields: [],
    connect: null,
});

export { createAndConnect, notifyWarning };
