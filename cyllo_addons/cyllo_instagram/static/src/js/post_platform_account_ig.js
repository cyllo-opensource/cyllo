/** @odoo-module **/
import { postPlatformAccountFields } from "@cyllo_social_media_marketing/js/post_platform_accounts";

postPlatformAccountFields.add("social.insta.account", {
    boolField: "post_on_instagram",
    accountField: "insta_account_ids",
    many2one: false,
    icon: "ri-instagram-line",
    color: "#C13584",
    allowedModes: ["url", "photo", "video"],
});
