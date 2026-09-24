/** @odoo-module **/
import { registry } from "@web/core/registry";





export const streamItemActions = registry.category("social_stream_item_actions");

export const streamTypeLabels = {
    posts: "Posts",
    videos: "Videos",
    comments: "Comments",
    mentions: "Mentions",
    unpublished: "Unpublished",
    hashtag_recent: "Hashtag - Recent",
    hashtag_trending: "Hashtag - Top",
    moderate: "Moderate",
    likely_spam: "Likely Spam",
    search: "Search",
    playlist: "Playlist",
};


export const streamPlatforms = registry.category("social_stream_platforms");

streamPlatforms.add("social.fb.account", {
    label: "Facebook",
    icon: "ri-facebook-fill",
    tabIcon: "ri-facebook-circle-line",
    modalIcon: "fa fa-facebook",
    color: "#1877f2",
    postField: "posted_on_facebook",
    audienceLabel: "followers",
    streamTypes: ["posts", "comments", "mentions", "unpublished"],
});

streamPlatforms.add("social.insta.account", {
    label: "Instagram",
    icon: "ri-instagram-line",
    tabIcon: "ri-instagram-line",
    modalIcon: "fa fa-instagram",
    color: "#c13584",
    postField: "posted_on_ig",
    audienceLabel: "followers",
    streamTypes: ["posts", "comments", "hashtag_recent", "hashtag_trending"],
});


export const streamTypesNeedingConfig = new Set(["hashtag_recent", "hashtag_trending", "search", "playlist"]);


export function reorderByDrop(items, draggedId, previousEl, nextEl) {
    const ids = items.map((item) => item.id);
    const draggedIndex = ids.indexOf(draggedId);
    if (draggedIndex === -1) {
        return ids;
    }
    ids.splice(draggedIndex, 1);
    let targetIndex;
    if (nextEl) {
        targetIndex = ids.indexOf(Number(nextEl.dataset.id));
    } else if (previousEl) {
        targetIndex = ids.indexOf(Number(previousEl.dataset.id)) + 1;
    } else {
        targetIndex = ids.length;
    }
    if (targetIndex === -1) {
        targetIndex = ids.length;
    }
    ids.splice(targetIndex, 0, draggedId);
    return ids;
}


export async function openLeadDialogResult(comp, data, uniqueFieldName, platform) {
    if (data.lead) {
        comp.action.doAction({
            type: "ir.actions.act_window",
            res_model: "crm.lead",
            res_id: data.lead,
            views: [[false, "form"]],
            target: "current",
        });
        return;
    }
    let sourceId = false;
    const sourceLabel = streamPlatforms.get(platform, false)?.label;
    if (sourceLabel) {
        const existing = await comp.orm.searchRead("utm.source", [["name", "=", sourceLabel]], ["id"], {
            limit: 1,
        });
        if (existing.length) {
            sourceId = existing[0].id;
        } else {
            const createdIds = await comp.orm.create("utm.source", [{ name: sourceLabel }]);
            sourceId = createdIds[0];
        }
    }
    comp.action.doAction({
        type: "ir.actions.act_window",
        res_model: "crm.lead",
        views: [[false, "form"]],
        target: "new",
        context: {
            default_name: data.contact_name,
            default_type: data.type,
            default_user_id: data.user_id,
            default_partner_id: data.partner_id,
            default_contact_name: data.contact_name,
            default_referred: data.name,
            default_source_id: sourceId,
            [`default_${uniqueFieldName}`]: data[uniqueFieldName],
            default_campaign_id: data.campaign_id || false,
        },
    });
}

export const youtubeSearchOrderOptions = [
    { value: "date", label: "Date Uploaded" },
    { value: "relevance", label: "Relevance" },
    { value: "rating", label: "Rating" },
    { value: "viewCount", label: "View Count" },
];
