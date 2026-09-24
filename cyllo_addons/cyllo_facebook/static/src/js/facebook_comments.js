/** @odoo-module **/
import { Component, onWillStart, useRef, useState, onMounted} from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class FacebookComments extends Component {
    static template = "cyllo_facebook.FacebookComments";
    setup() {
        onWillStart(this.onWillStart);
        this.actionService = useService("action");
        this.orm = useService("orm");
        this.comment_reply = useRef("fb_comment_reply_area");
        this.nextElementSibling = null
        this.state = useState({
            loadingFb: false,
            fb_comments: []
        })
        onMounted(() => {

            document.querySelectorAll("textarea").forEach((textarea) => {
                textarea.addEventListener("input", () => {
                    textarea.style.height = "auto";
                    textarea.style.height = textarea.scrollHeight + "px";
                });
            });
        })
    }
    async onWillStart() {
        const feedId = this.props.action.context.active_id;
        if (feedId) {
            const record = await this.orm.read(
                "social.media.post",
                [feedId],
                ["id", "fb_media_number"]
            );
            await this.orm.call("social.media.post", "action_compute_fb_likes_count", [], {feed: record[0].fb_media_number})
            this.state.fb_comments = await this.orm.call(
                "social.media.post", "get_facebook_comments", [], {feed: record[0].fb_media_number}
            )
        }
    }

    get FacebookCommentDetails() {
        return this.state.fb_comments
    }

    async onClickPost(){
        if (this.state.loadingFb === true) {
            return;
        }
        this.state.loadingFb = true;
        const feedId = this.props.action.context.active_id
        if (feedId) {
            const record = await this.orm.read(
                "social.media.post",
                [feedId],
                ["id", "fb_media_number"]
            );
            const comment_div = document.getElementById("fb_comment_area");
            const self = this
            await this.orm.call(
                "social.media.post", "post_facebook_comments", [], {
                    feed: record[0].fb_media_number,
                    comment: comment_div.value
                }
            ).then(async function (data) {
                self.state.fb_comments = await self.orm.call(
                    "social.media.post", "get_facebook_comments",
                    [], {feed: record[0].fb_media_number}
                )
                comment_div.value = ''
                self.state.loadingFb = false;
            })
            await this.orm.call("social.media.post", "action_compute_fb_likes_count", [], {feed: record[0].fb_media_number})
        }
    }

    async convertToLead(){
        var feed_id = this.props.action.context.active_id
        self=this
        var parentElementId=event.target.parentElement.id
        const matchingComment = this.state.fb_comments.find(comment => comment.id === parentElementId);
        await this.orm.call("social.media.post", "create_lead", [feed_id, matchingComment], {})
        .then(function(data) {
            if (data['lead']){
                self.actionService.doAction({
                    res_model: 'crm.lead',
                    res_id: data['lead'],
                    target: "current",
                    type: "ir.actions.act_window",
                    views: [[false, "form"]],
                });
            }
            else{
                self.actionService.doAction({
                    res_model: 'crm.lead',
                    target: "new",
                    type: "ir.actions.act_window",
                    views: [[false, "form"]],
                    context: {
                        default_name: data['name'],
                        default_type: 'lead',
                        default_user_id: data['user_id'],
                        default_partner_id: data['partner_id'],
                        default_contact_name: data['contact_name'],
                        default_unique_fb_comment_number: data['unique_fb_comment_number'],
                    },
                });
            }
        })
    }

    onClickReply(event) {
        const replyDiv = event.currentTarget.closest(".cy-social_marketComment-box").querySelector(".reply_div");
        if (replyDiv.classList.contains("d-none")){
            replyDiv.classList.remove("d-none")
        }
        else{
            replyDiv.classList.add("d-none")
        }
        this.nextElementSibling = replyDiv
    }

    onClickViewReplies(event) {
        const replies = event.currentTarget.closest(".cy-social_marketComment-box").querySelector(".view_replies");
        if (replies.classList.contains("d-none")){
            replies.classList.remove("d-none")
        }
        else{
            replies.classList.add("d-none")
        }
    }

    async postReply(comment){
        if (this.state.loadingFb === true) {
            return;
        }
        this.state.loadingFb = true;
        const feedId = this.props.action.context.active_id
        if (feedId) {
            const record = await this.orm.read(
                "social.media.post",
                [feedId],
                ["id", "fb_media_number"]
            );
            const self = this
            const comment_reply_div = document.getElementById(("comment_" + comment.id));
            await this.orm.call("social.media.post", "post_facebook_reply", [], {
                feed: record[0].fb_media_number,
                comment: comment.id,
                reply: comment_reply_div.value,
            }).then(async function (data) {
                self.state.fb_comments = await self.orm.call(
                    "social.media.post", "get_facebook_comments",
                    [], {feed: record[0].fb_media_number}
                )
                comment_reply_div.value = ''
                self.state.loadingFb = false;
                })
            await this.orm.call("social.media.post", "action_compute_fb_likes_count", [], {feed: record[0].fb_media_number})
        }
    }

    onClickDelete(){
        var fb_comment_id = event.target.parentElement.id
    }
}

registry.category("actions").add("fb_comments", FacebookComments);