/** @odoo-module **/
import { Component, useState, onWillUpdateProps } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { session } from "@web/session";
import { deserializeDateTime } from "@web/core/l10n/dates";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { usePopover } from "@web/core/popover/popover_hook";
import { EmojiPicker } from "@web/core/emoji_picker/emoji_picker";
import { InstagramEmbedDialog } from "./instagram_embed_dialog";
import { ShareDialog } from "./share_dialog";
import { streamItemActions, streamTypeLabels, streamPlatforms, streamTypesNeedingConfig } from "./stream_registry";
import { postPlatformAccountFields } from "../post_platform_accounts";

const OWN_POSTS_STREAM_TYPES = new Set(["posts", "videos"]);
const IG_CAPTION_TRUNCATE_LENGTH = 100;
const MAX_EMPTY_PAGE_AUTO_HOPS = 5;

export class StreamColumn extends Component {
    static template = "cyllo_social_media_marketing.StreamColumn";
    static components = { Dropdown, DropdownItem };
    static props = {
        column: Object,
        onDelete: Function,
        onEditStream: Function,
    };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.dialog = useService("dialog");
        this.action = useService("action");
        this.user = useService("user");
        this.emojiPopover = usePopover(EmojiPicker, { animation: false });
        this.state = useState({
            items: this._loadCachedItems(),
            cursor: null,
            loading: true,
            error: null,
            openComments: {},
            commentDraft: {},
            openReply: {},
            replyDraft: {},
            openReplies: {},
            openCaptions: {},
            carouselIndex: {},
        });

        this.load();

        onWillUpdateProps((nextProps) => {
            if (JSON.stringify(nextProps.column.config) !== JSON.stringify(this.props.column.config)) {
                this.state.cursor = null;
                this.load();
            }
        });
    }

    get platformIcon() {
        return streamPlatforms.get(this.props.column.platform, false)?.icon || "ri-global-line";
    }

    get typeLabel() {
        const base = streamTypeLabels[this.props.column.stream_type] || this.props.column.stream_type;
        const streamType = this.props.column.stream_type;
        const config = this.props.column.config || {};
        if (streamType === "search" && config.search_query) {
            return `${base}: ${config.search_query}`;
        }
        if ((streamType === "hashtag_recent" || streamType === "hashtag_trending") && config.hashtag) {
            return `${base}: #${config.hashtag}`;
        }
        return base;
    }

    get currentUserAvatarUrl() {
        return `/web/image?model=res.users&id=${this.user.userId}&field=avatar_128`;
    }

    get _commentsAdapter() {
        return streamPlatforms.get(this.props.column.platform, false)?.comments;
    }

    get likeIcon() {
        return this._commentsAdapter?.likeIcon || "ri-thumb-up-line";
    }

    get canReply() {
        return !!this._commentsAdapter?.canReply;
    }

    get canLike() {
        return !!streamPlatforms.get(this.props.column.platform, false)?.likePost;
    }

    async likeItem(item) {
        const likePost = streamPlatforms.get(this.props.column.platform, false)?.likePost;
        if (!likePost || item.liked) {
            return;
        }
        const res = await likePost(this, item);
        if (res && res.type === "ir.actions.client") {
            this.notification.add(res.params.message, { type: "danger" });
            return;
        }
        item.like_count = (item.like_count || 0) + 1;
        item.liked = true;
    }

    resolveActionLabel(action, item) {
        return typeof action.label === "function" ? action.label(item) : action.label;
    }

    get _cacheKey() {
        return `o_stream_column_cache_${session.db}_${this.props.column.id}`;
    }

    _loadCachedItems() {
        try {
            const raw = sessionStorage.getItem(this._cacheKey);
            return raw ? JSON.parse(raw) : [];
        } catch {
            return [];
        }
    }

    _saveCachedItems(items) {
        try {
            sessionStorage.setItem(this._cacheKey, JSON.stringify(items));
        } catch {
        }
    }

    getActionsFor(itemKind) {
        const prefix = this.props.column.platform + ":";
        return streamItemActions
            .getEntries()
            .filter(([key, action]) => key.startsWith(prefix) && action.itemKind === itemKind)
            .map(([, action]) => action);
    }

    async load(cursor) {
        this.state.loading = true;
        try {
            let nextCursor = cursor || false;
            let result;
            let hops = 0;
            do {
                result = await this.orm.call(
                    "social.stream.column",
                    "fetch_stream_data",
                    [[this.props.column.id]],
                    { cursor: nextCursor }
                );
                if (result && result.type === "ir.actions.client") {
                    this.notification.add(result.params.message, { type: result.params.type || "warning" });
                    this.state.error = result.params.message;
                    return;
                }
                nextCursor = result.cursor || false;
                hops++;
            } while ((result.items || []).length === 0 && nextCursor && hops < MAX_EMPTY_PAGE_AUTO_HOPS);

            if (cursor) {
                const seenIds = new Set(this.state.items.map((i) => i.id));
                const newItems = (result.items || []).filter((i) => !seenIds.has(i.id));
                this.state.items.push(...newItems);
            } else {
                this.state.items = result.items || [];
                this._saveCachedItems(this.state.items);
            }
            this.state.cursor = result.cursor || null;
            this.state.error = null;
        } finally {
            this.state.loading = false;
        }
    }

    onCarouselScroll(ev, item) {
        const track = ev.target;
        this.state.carouselIndex[item.id] = Math.round(track.scrollLeft / track.clientWidth);
    }

    scrollCarousel(ev, direction) {
        ev.stopPropagation();
        const track = ev.currentTarget.closest(".o_stream_item_carousel").querySelector(".o_stream_item_carousel_track");
        track.scrollBy({ left: direction * track.clientWidth, behavior: "smooth" });
    }

    refresh() {
        this.state.cursor = null;
        this.load();
    }

    loadMore() {
        if (this.state.cursor) {
            this.load(this.state.cursor);
        }
    }

    viewAccount() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: this.props.column.platform,
            res_id: this.props.column.account_res_id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    get canCreatePost() {
        const column = this.props.column;
        return OWN_POSTS_STREAM_TYPES.has(column.stream_type) && !!postPlatformAccountFields.get(column.platform, false);
    }

    createPost() {
        const column = this.props.column;
        const config = postPlatformAccountFields.get(column.platform, false);
        if (!config) {
            return;
        }
        const context = {[`default_${config.boolField}`]: true };
        context[`default_${config.accountField}`] = config.many2one
            ? [column.account_res_id, column.account_display_name]
            : [[6, 0, [column.account_res_id]]];
        this.action.doAction({
            name: "New Post",
            type: "ir.actions.act_window",
            res_model: "social.media.post",
            views: [[false, "form"]],
            target: "current",
            context,
        });
    }

    get canEditConfig() {
        return streamTypesNeedingConfig.has(this.props.column.stream_type);
    }

    editStream() {
        this.props.onEditStream(this.props.column);
    }

    deleteColumn() {
        this.dialog.add(ConfirmationDialog, {
            title: "Remove stream",
            body: "Remove this stream from the board?",
            confirm: () => {
                try {
                    sessionStorage.removeItem(this._cacheKey);
                } catch {
                }
                return this.props.onDelete(this.props.column.id);
            },
            cancel: () => { },
        });
    }

    formatDate(dateStr) {
        if (!dateStr) {
            return "";
        }
        try {
            const parsed = deserializeDateTime(dateStr);
            return parsed.isValid ? parsed.toFormat("dd MMM yyyy, HH:mm") : dateStr;
        } catch {
            return dateStr;
        }
    }

    formatRelativeDate(dateStr) {
        if (!dateStr) {
            return "";
        }
        try {
            const parsed = deserializeDateTime(dateStr);
            return parsed.isValid ? parsed.toRelative() : dateStr;
        } catch {
            return dateStr;
        }
    }

    openInstagramEmbed(item) {
        if (!item.permalink) {
            return;
        }
        this.dialog.add(InstagramEmbedDialog, { permalink: item.permalink });
    }

    openShareDialog(item) {
        this.dialog.add(ShareDialog, {
            text: item.text || "",
            permalink: item.permalink || "",
        });
    }

    captionTruncated(text) {
        return !!text && text.length > IG_CAPTION_TRUNCATE_LENGTH;
    }

    captionPreview(text) {
        return text.slice(0, IG_CAPTION_TRUNCATE_LENGTH).trimEnd();
    }

    toggleCaption(item) {
        this.state.openCaptions[item.id] = !this.state.openCaptions[item.id];
    }

    formatDuration(iso) {
        if (!iso) {
            return "";
        }
        const match = /^PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$/.exec(iso);
        if (!match) {
            return "";
        }
        const hours = match[1];
        const minutes = match[2] || "0";
        const seconds = match[3] || "0";
        const pad = (val) => (val.length < 2 ? "0" + val : val);
        return hours ? `${hours}:${pad(minutes)}:${pad(seconds)}` : `${minutes}:${pad(seconds)}`;
    }

    toggleComments(item) {
        if (this.state.openComments[item.id]) {
            delete this.state.openComments[item.id];
            return;
        }
        this.state.openComments[item.id] = { loading: true, comments: [], cursor: null, error: null };
        this.loadComments(item);
    }

    loadMoreComments(item) {
        const entry = this.state.openComments[item.id];
        if (entry && entry.cursor && !entry.loading) {
            this.loadComments(item, entry.cursor);
        }
    }

    _commentExtra(item, userKey, userValue) {
        return {
            parent_title: item.text,
            parent_permalink: item.permalink,
            [userKey]: userValue,
            lead_id: false,
        };
    }

    async loadComments(item, cursor) {
        const entry = this.state.openComments[item.id];
        entry.loading = true;
        try {
            const adapter = this._commentsAdapter;
            const { items, nextCursor } = adapter?.fetchComments
                ? await adapter.fetchComments(this, item, cursor)
                : { items: [], nextCursor: null };
            if (cursor) {
                const seenIds = new Set(entry.comments.map((c) => c.id));
                entry.comments.push(...items.filter((c) => !seenIds.has(c.id)));
            } else {
                entry.comments = items;
            }
            entry.cursor = nextCursor;
            entry.error = null;
        } catch (e) {
            entry.error = e.message || "Could not load comments.";
        } finally {
            entry.loading = false;
        }
    }

    _replyExtra(comment, userKey, userValue) {
        return {
            parent_title: comment.extra?.parent_title,
            parent_permalink: comment.extra?.parent_permalink,
            [userKey]: userValue,
            lead_id: false,
        };
    }

    toggleReplies(comment) {
        if (this.state.openReplies[comment.id]) {
            delete this.state.openReplies[comment.id];
            return;
        }
        this.state.openReplies[comment.id] = { loading: true, replies: [], cursor: null, error: null };
        this.loadReplies(comment);
    }

    loadMoreReplies(comment) {
        const entry = this.state.openReplies[comment.id];
        if (entry && entry.cursor && !entry.loading) {
            this.loadReplies(comment, entry.cursor);
        }
    }

    async loadReplies(comment, cursor) {
        const entry = this.state.openReplies[comment.id];
        entry.loading = true;
        try {
            const adapter = this._commentsAdapter;
            const { items, nextCursor } = adapter?.fetchReplies
                ? await adapter.fetchReplies(this, comment, cursor)
                : { items: [], nextCursor: null };
            if (cursor) {
                const seenIds = new Set(entry.replies.map((r) => r.id));
                entry.replies.push(...items.filter((r) => !seenIds.has(r.id)));
            } else {
                entry.replies = items;
            }
            entry.cursor = nextCursor;
            entry.error = null;
        } catch (e) {
            entry.error = e.message || "Could not load replies.";
        } finally {
            entry.loading = false;
        }
    }

    async submitComment(item) {
        const text = (this.state.commentDraft[item.id] || "").trim();
        if (!text) {
            return;
        }
        const adapter = this._commentsAdapter;
        const res = adapter?.postComment ? await adapter.postComment(this, item, text) : undefined;
        if (res && res.type === "ir.actions.client") {
            this.notification.add(res.params.message, { type: "danger" });
            return;
        }
        this.state.commentDraft[item.id] = "";
        const entry = this.state.openComments[item.id];
        entry.comments = [this._optimisticComment(text, item.text, item.permalink), ...entry.comments];
        item.comment_count = (item.comment_count || 0) + 1;
    }

    _optimisticComment(text, parentTitle, parentPermalink) {
        const column = this.props.column;
        return {
            id: `local-${Date.now()}`,
            author_name: column.account_display_name,
            author_avatar_url: column.account_avatar_url,
            text,
            created_at: "Just now",
            like_count: 0,
            reply_count: 0,
            replies: [],
            extra: {
                parent_title: parentTitle,
                parent_permalink: parentPermalink,
                lead_id: false,
            },
        };
    }

    openEmojiPicker(ev, draft, id) {
        this.emojiPopover.open(ev.currentTarget, {
            onSelect: (codepoints) => {
                draft[id] = (draft[id] || "") + codepoints;
            },
        });
    }

    toggleReply(item) {
        this.state.openReply[item.id] = !this.state.openReply[item.id];
    }

    getReplyTargetId(reply, rootId) {
        return this._commentsAdapter?.getReplyTargetId?.(reply, rootId) ?? rootId;
    }

    async submitReply(item, replyToId, rootComment) {
        const text = (this.state.replyDraft[item.id] || "").trim();
        if (!text) {
            return;
        }
        const targetId = replyToId ?? item.id;
        const root = rootComment || item;
        const adapter = this._commentsAdapter;
        const res = adapter?.postReply ? await adapter.postReply(this, item, targetId, text) : undefined;
        if (res && res.type === "ir.actions.client") {
            this.notification.add(res.params.message, { type: "danger" });
            return;
        }
        this.state.replyDraft[item.id] = "";
        this.state.openReply[item.id] = false;
        this.notification.add("Reply posted.", { type: "success" });
        if (!this.state.openReplies[root.id]) {
            this.state.openReplies[root.id] = { loading: false, replies: [], cursor: null, error: null };
        }
        const entry = this.state.openReplies[root.id];
        entry.replies = [...entry.replies, this._optimisticComment(text, root.extra?.parent_title, root.extra?.parent_permalink)];
        root.reply_count = (root.reply_count || 0) + 1;
    }
}
