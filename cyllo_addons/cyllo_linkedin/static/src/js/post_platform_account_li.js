/** @odoo-module **/
import { postPlatformAccountFields } from "@cyllo_social_media_marketing/js/post_platform_accounts";

postPlatformAccountFields.add("linkedin.organization", {
    boolField: "posted_on_linkedin",
    accountField: "linkedin_organization_ids",
    many2one: false,
    icon: "ri-linkedin-fill",
    color: "#0A66C2",
    allowedModes: ["photo", "content_only", "poll"],
});
