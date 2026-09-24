/** @odoo-module **/
import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import {
    streamPlatforms,
    streamTypeLabels,
    streamTypesNeedingConfig,
    youtubeSearchOrderOptions,
} from "./stream_registry";

export class AddStreamPanel extends Component {
    static template = "cyllo_social_media_marketing.AddStreamPanel";
    static props = {
        boardId: Number,
        editColumn: { type: [Object, Boolean], optional: true },
        onAdded: Function,
        onClose: Function,
    };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.streamPlatforms = streamPlatforms;
        this.streamTypeLabels = streamTypeLabels;
        this.youtubeSearchOrderOptions = youtubeSearchOrderOptions;

        const editColumn = this.props.editColumn;
        const config = editColumn?.config || {};
        this.state = useState({
            step: editColumn ? "config" : "account",
            accounts: [],
            loading: !editColumn,
            selectedAccount: editColumn
                ? {
                      platform: editColumn.platform,
                      id: editColumn.account_res_id,
                      name: editColumn.account_display_name,
                      avatar_url: editColumn.account_avatar_url,
                  }
                : null,
            selectedType: editColumn ? editColumn.stream_type : null,
            hashtag: config.hashtag || "",
            searchQuery: config.search_query || "",
            searchOrder: config.order || "date",
            playlists: [],
            loadingPlaylists: !!editColumn && editColumn.stream_type === "playlist",
            selectedPlaylistId: config.playlist_id || "",
            saving: false,
        });

        if (editColumn) {
            if (editColumn.stream_type === "playlist") {
                this._loadPlaylists(editColumn.account_res_id);
            }
        } else {
            this._loadAccounts();
        }
    }

    async _loadAccounts() {
        this.state.accounts = await this.orm.call("social.media.post", "get_streamable_accounts", []);
        this.state.loading = false;
    }

    async _loadPlaylists(accountResId) {
        this.state.playlists = await this.orm.call("social.media.post", "get_youtube_channel_playlists", [
            accountResId,
        ]);
        this.state.loadingPlaylists = false;
    }

    get groupedAccounts() {
        const groups = {};
        for (const account of this.state.accounts) {
            if (!groups[account.platform]) {
                groups[account.platform] = [];
            }
            groups[account.platform].push(account);
        }
        return Object.entries(groups);
    }

    get typesForSelectedPlatform() {
        if (!this.state.selectedAccount) {
            return [];
        }
        return streamPlatforms.get(this.state.selectedAccount.platform, false)?.streamTypes || [];
    }

    needsConfig(streamType) {
        return streamTypesNeedingConfig.has(streamType);
    }

    selectAccount(account) {
        this.state.selectedAccount = account;
        this.state.step = "type";
    }

    async selectType(streamType) {
        this.state.selectedType = streamType;
        if (streamType === "playlist") {
            this.state.loadingPlaylists = true;
            await this._loadPlaylists(this.state.selectedAccount.id);
        }
        if (this.needsConfig(streamType)) {
            this.state.step = "config";
        } else {
            await this.finish();
        }
    }

    back() {
        if (this.props.editColumn) {
            return;
        }
        if (this.state.step === "config") {
            this.state.step = "type";
        } else if (this.state.step === "type") {
            this.state.selectedAccount = null;
            this.state.step = "account";
        }
    }

    async finish() {
        const streamType = this.state.selectedType;
        let config = {};
        if (streamType === "hashtag_recent" || streamType === "hashtag_trending") {
            const hashtag = this.state.hashtag.trim().replace(/^#/, "");
            if (!hashtag) {
                this.notification.add("Enter a hashtag first.", { type: "warning" });
                return;
            }
            config = { hashtag };
        } else if (streamType === "search") {
            const query = this.state.searchQuery.trim();
            if (!query) {
                this.notification.add("Enter a search keyword first.", { type: "warning" });
                return;
            }
            config = { search_query: query, order: this.state.searchOrder };
        } else if (streamType === "playlist") {
            if (!this.state.selectedPlaylistId) {
                this.notification.add("Choose a playlist first.", { type: "warning" });
                return;
            }
            config = { playlist_id: this.state.selectedPlaylistId };
        }
        this.state.saving = true;
        try {
            if (this.props.editColumn) {
                await this.orm.write("social.stream.column", [this.props.editColumn.id], {
                    config: JSON.stringify(config),
                });
                await this.props.onAdded({ ...this.props.editColumn, config });
            } else {
                const account = this.state.selectedAccount;
                const column = await this.orm.call("social.stream.column", "create_column", [], {
                    board_id: this.props.boardId,
                    platform: account.platform,
                    account_res_id: account.id,
                    stream_type: streamType,
                    account_display_name: account.name,
                    account_avatar_url: account.avatar_url,
                    config,
                });
                await this.props.onAdded(column);
            }
        } finally {
            this.state.saving = false;
        }
    }
}
