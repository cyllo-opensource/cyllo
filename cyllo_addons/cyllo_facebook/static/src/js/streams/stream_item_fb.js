/** @odoo-module **/
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import {
    streamItemActions,
    streamPlatforms,
    openLeadDialogResult,
} from "@cyllo_social_media_marketing/js/streams/stream_registry";







streamPlatforms.add("social.fb.account", {
    ...streamPlatforms.get("social.fb.account", {}),
    likePost: (comp, item) => comp.orm.call("social.media.post", "post_facebook_like", [], {
        post_id: item.id,
        account_res_id: comp.props.column.account_res_id,
    }),
    comments: {
        likeIcon: "ri-thumb-up-line",
        canReply: true,
        getReplyTargetId: (reply, rootId) => reply.id,

        async fetchComments(comp, item, cursor) {
            const column = comp.props.column;
            const res = await comp.orm.call("social.media.post", "get_facebook_comments", [], {
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
                created_at: c.created_time,
                like_count: c.like_count,
                reply_count: c.reply_count || 0,
                replies: [],
                extra: comp._commentExtra(item, "userid", c.userid),
            }));
            return { items, nextCursor: res.paging?.next || null };
        },

        async fetchReplies(comp, comment, cursor) {
            const column = comp.props.column;
            const res = await comp.orm.call("social.media.post", "get_facebook_comment_replies", [], {
                comment_id: comment.id,
                cursor: cursor || false,
                account_res_id: column.account_res_id,
            });
            if (res.type === "ir.actions.client") {
                throw new Error(res.params.message);
            }
            const toReplyItem = (r) => ({
                id: r.id,
                author_name: r.from?.name,
                author_avatar_url: false,
                text: r.message,
                created_at: r.created_time,
                like_count: r.like_count || 0,
                replies: (r.comments?.data || []).map(toReplyItem),
                extra: comp._replyExtra(comment, "userid", r.from?.id),
            });
            const items = (res.data || []).map(toReplyItem);
            return { items, nextCursor: res.paging?.next || null };
        },

        async postComment(comp, item, text) {
            return comp.orm.call("social.media.post", "post_facebook_comments", [], {
                feed: item.id,
                comment: text,
            });
        },

        async postReply(comp, item, targetId, text) {
            return comp.orm.call("social.media.post", "post_facebook_reply", [], {
                comment: targetId,
                reply: text,
            });
        },
    },
}, { force: true });

streamItemActions.add("social.fb.account:delete_comment", {
    icon: "ri-delete-bin-line",
    label: "Delete",
    itemKind: "comment_thread",
    handler: (item, column, comp) => {
        comp.dialog.add(ConfirmationDialog, {
            title: "Delete comment",
            body: "Delete this comment?",
            confirm: async () => {
                await comp.orm.call("social.media.post", "delete_facebook_comment", [], { comment_id: item.id });
                comp.state.items = comp.state.items.filter((i) => i.id !== item.id);
            },
            cancel: () => {},
        });
    },
});

streamItemActions.add("social.fb.account:create_lead", {
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
        const data = await comp.orm.call("social.media.post", "create_lead", [
            [],
            commentData,
            item.extra?.parent_title,
        ]);
        openLeadDialogResult(comp, data, "unique_fb_comment_number", "social.fb.account");
    },
});
