/** @odoo-module **/
import { connectAccountPlatforms } from "@cyllo_social_media_marketing/js/platform_registry";

const linkedinFields = [
    { key: "linkedin_account_name", label: "Account Name", type: "text", placeholder: "Enter a name for this LinkedIn account" },
    { key: "linkedin_username", label: "Email ID", type: "text", placeholder: "Enter LinkedIn Email" },
    { key: "linkedin_client_id", label: "Client ID", type: "text", required: true, placeholder: "Enter LinkedIn App Client ID" },
    { key: "linkedin_client_secret", label: "Client Secret", type: "text", required: true, placeholder: "Enter LinkedIn App Client Secret" },
];

connectAccountPlatforms.add("linkedin.account", {
    ...connectAccountPlatforms.get("linkedin.account", {}),
    fields: linkedinFields,
    note: () => "You will be redirected to LinkedIn to authorize Cyllo - the access token is fetched automatically.",
    async connect(comp, values) {
        const action = await comp.orm.call("linkedin.account", "get_linkedin_auth_url", [], {
            account_id: false,
            username: values.linkedin_username,
            client_id: values.linkedin_client_id,
            client_secret: values.linkedin_client_secret,
        });
        comp.action.doAction(action);
    },
}, { force: true });
