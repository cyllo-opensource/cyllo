/** @odoo-module **/
import {
    streamItemActions,
    streamPlatforms,
    openLeadDialogResult,
} from "@cyllo_social_media_marketing/js/streams/stream_registry";



streamPlatforms.add("social.insta.account", {
    ...streamPlatforms.get("social.insta.account", {}),
    comments: {
        likeIcon: "ri-heart-line",
        canReply: true,
        getReplyTargetId: (reply, rootId) => rootId,

        async fetchComments(comp, item, cursor) {
            const column = comp.props.column;
            const res = await comp.orm.call("social.media.post", "get_instagram_comments", [], {
                feed: item.id,
                account_res_id: column.account_res_id,
                nextUrl: cursor || false,
            });
            if (res.type === "ir.actions.client") {
                throw new Error(res.params.message);
            }
            const items = (res.data || []).map((c) => ({
                id: c.id,
                author_name: c.username,
                author_avatar_url: false,
                text: c.text,
                created_at: c.timestamp,
                like_count: c.like_count,
                reply_count: c.reply_count || 0,
                replies: [],
                extra: comp._commentExtra(item, "from_id", c.from?.id),
            }));
            return { items, nextCursor: res.paging?.next || null };
        },

        async fetchReplies(comp, comment, cursor) {
            const column = comp.props.column;
            const res = await comp.orm.call("social.media.post", "get_instagram_comment_replies", [], {
                comment_id: comment.id,
                cursor: cursor || false,
                account_res_id: column.account_res_id,
            });
            if (res.type === "ir.actions.client") {
                throw new Error(res.params.message);
            }
            const items = (res.data || []).map((r) => ({
                id: r.id,
                author_name: r.username,
                text: r.text,
                created_at: r.timestamp,
                like_count: r.like_count,
                extra: comp._replyExtra(comment, "from_id", r.from?.id),
            }));
            return { items, nextCursor: res.paging?.next || null };
        },

        async postComment(comp, item, text) {
            return comp.orm.call("social.media.post", "post_instagram_comments", [], {
                feed: item.id,
                comment: text,
            });
        },

        async postReply(comp, item, targetId, text) {
            return comp.orm.call("social.media.post", "post_instagram_reply", [], {
                comment: targetId,
                reply: text,
            });
        },
    },
}, { force: true });

streamItemActions.add("social.insta.account:create_lead", {
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
        const commentData = {
            id: item.id,
            username: item.author_name,
            from: { id: item.extra?.from_id },
        };
        const data = await comp.orm.call("social.media.post", "create_lead_ig", [
            [],
            commentData,
            item.extra?.parent_title,
        ]);
        openLeadDialogResult(comp, data, "unique_ig_comment_number", "social.insta.account");
    },
});
