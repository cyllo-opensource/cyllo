/** @odoo-module **/
import { postPlatformAccountFields } from "@cyllo_social_media_marketing/js/post_platform_accounts";

postPlatformAccountFields.add("social.fb.account", {
    boolField: "post_on_facebook",
    accountField: "fb_account_ids",
    many2one: false,
    icon: "ri-facebook-fill",
    color: "#1877f2",
    allowedModes: ["url", "photo", "content_only"],
});
