/** @odoo-module **/
import { Component, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class YoutubeComment extends Component {
    static template = "cyllo_youtube.YoutubeComment";
    setup() {
        onWillStart(this.onWillStart);
        this.orm = useService("orm");
        this.actionService = useService("action");
    }
    async onWillStart() {
        var feed_id = this.props.action.context.active_id
        var self = this;
        self.youtube_comment = await this.orm.call(
            "social.media.post", "get_youtube_comments", ["", feed_id], {})
    }
    get YoutubeCommentDetails() {
        return this.youtube_comment
    }
    async onClickPost() {
        var feed_id = this.props.action.context.active_id
        var self = this;
        var comment_div = document.getElementById("yt_comment_area");
        await this.orm.call(
            "social.media.post", "post_youtube_comments", ["", feed_id, comment_div.value], {}
        ).then(function(data) {
            comment_div.value = ''
        })
        window.location.reload();
    }
    async convertToLead() {
        var feed_id = this.props.action.context.active_id
        self = this
        var parentElementId = event.target.parentElement.id
        const matchingComment = this.youtube_comment.find(comment => comment.id === parentElementId);
        await this.orm.call(
                "social.media.post", "create_lead_youtube", [feed_id, matchingComment], {})
            .then(function(data) {
                if (data['lead']) {
                    self.actionService.doAction({
                        res_model: 'crm.lead',
                        res_id: data['lead'],
                        target: "current",
                        type: "ir.actions.act_window",
                        views: [
                            [false, "form"]
                        ],
                    }, );
                } else {
                    self.actionService.doAction({
                        res_model: 'crm.lead',
                        target: "new",
                        type: "ir.actions.act_window",
                        views: [
                            [false, "form"]
                        ],
                        context: {
                            default_name: data['name'],
                            default_type: 'lead',
                            default_user_id: data['user_id'],
                            default_partner_id: data['partner_id'],
                            default_contact_name: data['contact_name'],
                            default_unique_ig_comment_number: data['youtube_number'],
                        },
                    }, );
                }
            })
    }
    onClickViewReplies(ev) {
        var style = ev.target.nextElementSibling.style
        if (style.display == 'none') {
            ev.target.nextElementSibling.style = 'block'
        } else {
            ev.target.nextElementSibling.style = 'none'
        }
    }
    async postReply() {
        var comment_id = event.target.parentElement.id
        var feed_id = this.props.action.context.active_id
        var comment_reply_div = event.target.parentElement.firstChild
        await this.orm.call(
            "social.media.post", "post_youtube_reply",
            ["", feed_id, comment_id, comment_reply_div.value], {}
        ).then(function(data) {
            comment_reply_div.value = ''
        })
    }
    onClickReply() {
        event.target.nextElementSibling.style = 'block'
    }
    onClickDelete() {
        var yt_comment_id = event.target.parentElement.id
    }
}
registry.category("actions").add("youtube_comments", YoutubeComment);
