/** @odoo-module **/
import {
    streamItemActions,
    streamPlatforms,
    openLeadDialogResult,
} from "@cyllo_social_media_marketing/js/streams/stream_registry";

streamPlatforms.add("youtube.channel", {
    label: "YouTube",
    icon: "ri-youtube-fill",
    tabIcon: "ri-youtube-line",
    modalIcon: "fa fa-youtube",
    color: "#ff0000",
    postField: "posted_on_youtube",
    audienceLabel: "subscribers",
    streamTypes: ["videos", "comments", "moderate", "likely_spam", "search", "playlist"],
    comments: {
        likeIcon: "ri-thumb-up-line",
        canReply: true,
        getReplyTargetId: (reply, rootId) => rootId,

        async fetchComments(comp, item, cursor) {
            const column = comp.props.column;
            const res = await comp.orm.call("social.media.post", "get_youtube_comments", [
                item.id,
                cursor || null,
                column.account_res_id,
            ]);
            if (res.error) {
                throw new Error(res.error);
            }
            const items = (res.comments || []).map((c) => ({
                id: c.id,
                author_name: c.username,
                author_avatar_url: c.author_profile_img,
                text: c.text,
                created_at: c.publishedAt,
                like_count: c.likeCount,
                reply_count: c.reply_count || 0,
                replies: [],
                extra: comp._commentExtra(item, "userid", c.userid),
            }));
            return { items, nextCursor: res.nextPageToken || null };
        },

        async fetchReplies(comp, comment, cursor) {
            const column = comp.props.column;
            const res = await comp.orm.call("social.media.post", "get_youtube_comment_replies", [
                comment.id,
                cursor || null,
                column.account_res_id,
            ]);
            if (res.error) {
                throw new Error(res.error);
            }
            const items = (res.replies || []).map((r) => ({
                id: r.id,
                author_name: r.author,
                author_avatar_url: r.author_profile_img,
                text: r.text,
                created_at: r.publishedAt,
                like_count: r.likeCount,
                extra: comp._replyExtra(comment, "userid", r.userid),
            }));
            return { items, nextCursor: res.nextPageToken || null };
        },

        async postComment(comp, item, text) {
            const column = comp.props.column;
            return comp.orm.call("social.media.post", "post_youtube_comments", [item.id, text, column.account_res_id]);
        },

        async postReply(comp, item, targetId, text) {
            const column = comp.props.column;
            return comp.orm.call("social.media.post", "post_youtube_reply", [
                item.id,
                targetId,
                text,
                column.account_res_id,
            ]);
        },
    },
});

streamItemActions.add("youtube.channel:create_lead", {
    icon: "ri-user-add-line",
    label: (item) => (item?.extra?.lead_id ? "View Lead" : "Create Lead"),
    itemKind: "comment_thread",
    handler: async (item, column, comp) => {
        if (item.extra?.lead_id) {
            comp.action.doAction({
                type: "ir.actions.act_window",
                res_model: "crm.lead",
                res_id: item.extra.lead_id,
                views: [[false, "form"]],
                target: "current",
            });
            return;
        }
        const commentData = { id: item.id, username: item.author_name, userid: item.extra?.userid };
        const data = await comp.orm.call("social.media.post", "create_lead_youtube", [
            [],
            commentData,
            item.extra?.parent_title,
        ]);
        openLeadDialogResult(comp, data, "unique_yt_comment_number", "youtube.channel");
    },
});
