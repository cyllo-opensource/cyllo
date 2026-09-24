/** @odoo-module **/
import { streamPlatforms } from "@cyllo_social_media_marketing/js/streams/stream_registry";

streamPlatforms.add("linkedin.account", {
    label: "LinkedIn",
    icon: "ri-linkedin-fill",
    tabIcon: "ri-linkedin-box-line",
    modalIcon: "fa fa-linkedin",
    color: "#0a66c2",
    postField: "posted_on_linkedin",
    audienceLabel: "followers",
    streamTypes: ["posts", "comments"],
    comments: {
        likeIcon: "ri-thumb-up-line",
        canReply: false,

        async fetchComments(comp, item) {
            const column = comp.props.column;
            const res = await comp.orm.call("linkedin.account", "action_fetch_feed_comments", [
                [column.account_res_id],
                item.id,
            ]);
            const items = (res || []).map((c) => ({
                id: c.id,
                author_name: c.author_name,
                author_avatar_url: false,
                text: c.text,
                created_at: c.created_at,
                like_count: c.likes_count,
            }));
            return { items, nextCursor: null };
        },

        async postComment(comp, item, text) {
            const column = comp.props.column;
            return comp.orm.call("linkedin.account", "action_post_linkedin_comment", [
                [column.account_res_id],
                item.id,
                text,
            ]);
        },
    },
});







streamPlatforms.add("linkedin.organization", {
    label: "LinkedIn",
    icon: "ri-linkedin-fill",
    tabIcon: "ri-linkedin-box-line",
    modalIcon: "fa fa-linkedin",
    color: "#0a66c2",
    streamTypes: ["posts", "comments"],
    comments: {
        likeIcon: "ri-thumb-up-line",
        canReply: false,

        async fetchComments(comp, item) {
            const column = comp.props.column;
            const res = await comp.orm.call("linkedin.organization", "action_fetch_feed_comments", [
                [column.account_res_id],
                item.id,
            ]);
            const items = (res || []).map((c) => ({
                id: c.id,
                author_name: c.author_name,
                author_avatar_url: false,
                text: c.text,
                created_at: c.created_at,
                like_count: c.likes_count,
            }));
            return { items, nextCursor: null };
        },

        async postComment(comp, item, text) {
            const column = comp.props.column;
            return comp.orm.call("linkedin.organization", "action_post_linkedin_comment", [
                [column.account_res_id],
                item.id,
                text,
            ]);
        },
    },
});
