/** @odoo-module **/
import { postPlatformAccountFields } from "@cyllo_social_media_marketing/js/post_platform_accounts";

postPlatformAccountFields.add("youtube.channel", {
    boolField: "post_on_youtube",
    accountField: "youtube_channel_id",
    many2one: true,
    icon: "ri-youtube-fill",
    color: "#FF0000",
    allowedModes: ["video"],
});
