/** @odoo-module **/
import { Component, useState, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

const LIVE_SYNC_INTERVAL = 400;

export class SocialPostPreview extends Component {
    static template = "cyllo_social_media_marketing.SocialPostPreview";
    static props = { ...standardWidgetProps };

    setup() {
        this.user = useService("user");
        this.state = useState({ carouselIndex: 0 });
        let intervalId;
        onMounted(() => {
            intervalId = setInterval(() => {
                this.props.record.model.bus.trigger("NEED_LOCAL_CHANGES", { proms: [] });
            }, LIVE_SYNC_INTERVAL);
        });
        onWillUnmount(() => clearInterval(intervalId));
    }

    get mode() {
        return this.props.record.data.mode;
    }

    get description() {
        return this.props.record.data.description || "";
    }

    get attachments() {
        const m2m = this.props.record.data.ir_attachment_ids;
        return m2m ? m2m.records : [];
    }

    get firstAttachment() {
        return this.attachments[0];
    }

    get imageAttachments() {
        if (this.mode !== "photo") {
            return [];
        }
        return this.attachments.filter((att) => (att.data.mimetype || "").startsWith("image/"));
    }

    get imageUrls() {
        return this.imageAttachments.map((att) => `/web/content/${att.resId}`);
    }

    onCarouselScroll(ev) {
        const track = ev.target;
        this.state.carouselIndex = Math.round(track.scrollLeft / track.clientWidth);
    }

    scrollCarousel(ev, direction) {
        ev.stopPropagation();
        const track = ev.currentTarget.closest(".o_social_post_preview_carousel").querySelector(".o_social_post_preview_carousel_track");
        track.scrollBy({ left: direction * track.clientWidth, behavior: "smooth" });
    }

    get isVideoAttachment() {
        const att = this.firstAttachment;
        if (!!att && (att.data.mimetype || "").startsWith("video/")) return true;
        const url = this.props.record.data.post_url
        const videoExtensions = [".mp4", ".webm", ".ogg", ".mov", ".mkv"];
            return (!!url && videoExtensions.some(ext => url.includes(ext)))
    }

    get mediaUrl() {
        if (this.mode === "url") {
            return this.props.record.data.post_url || false;
        }
        if ((this.mode === "photo" || this.mode === "video") && this.firstAttachment) {
            return `/web/content/${this.firstAttachment.resId}`;
        }
        return false;
    }

    get isPoll() {
        return this.mode === "poll";
    }

    get pollQuestion() {
        return this.props.record.data.linkedin_poll_question || "";
    }

    get pollOptions() {
        return [
            this.props.record.data.linkedin_poll_option_1,
            this.props.record.data.linkedin_poll_option_2,
            this.props.record.data.linkedin_poll_option_3,
            this.props.record.data.linkedin_poll_option_4,
        ].filter(Boolean);
    }

    get pollDurationLabel() {
        const value = this.props.record.data.linkedin_poll_duration;
        if (!value) {
            return "";
        }
        const field = this.props.record.fields.linkedin_poll_duration;
        const match = field && field.selection && field.selection.find(([v]) => v === value);
        return match ? match[1] : value;
    }

    get currentUserAvatarUrl() {
        return `/web/image?model=res.users&id=${this.user.userId}&field=avatar_128`;
    }

    get currentUserName() {
        return this.user.name;
    }
}

registry.category("view_widgets").add("social_post_preview", {
    component: SocialPostPreview,
});
