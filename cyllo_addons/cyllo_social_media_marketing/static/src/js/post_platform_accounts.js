/** @odoo-module **/
import { Component, useState, onWillStart, useEffect } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";


export const postPlatformAccountFields = registry.category("post_platform_account_fields");


export class PostPlatformAccounts extends Component {
    static template = "cyllo_social_media_marketing.PostPlatformAccounts";
    static props = { ...standardWidgetProps };

    setup() {
        this.orm = useService("orm");
        this.state = useState({ accounts: [] });
        onWillStart(async () => {
            this.state.accounts = await this.orm.call("social.media.post", "get_connected_accounts", []);
            await this._syncHasSelectedPlatform();
        });
        useEffect(
            () => {
                (async () => {
                    for (const account of this.state.accounts) {
                        if (this.isModeDisabled(account) && this.isSelected(account)) {
                            await this.toggle(account);
                        }
                    }
                })();
            },
            () => [this.props.record.data.mode, this.state.accounts.length]
        );
    }

    _config(platform) {
        return postPlatformAccountFields.get(platform, false);
    }

    isModeDisabled(account) {
        const config = this._config(account.platform);
        const mode = this.props.record.data.mode;
        return !!config && !!config.allowedModes && !!mode && !config.allowedModes.includes(mode);
    }

    accountIcon(account) {
        return this._config(account.platform)?.icon || "ri-global-line";
    }

    accountColor(account) {
        return this._config(account.platform)?.color || "#849600";
    }

    isSelected(account) {
        const config = this._config(account.platform);
        if (!config) {
            return false;
        }
        const fieldValue = this.props.record.data[config.accountField];
        if (config.many2one) {
            return !!fieldValue && fieldValue[0] === account.id;
        }
        return !!fieldValue && fieldValue.currentIds.includes(account.id);
    }

    async toggle(account) {
        if (this.props.readonly) {
            return;
        }
        const config = this._config(account.platform);
        if (!config) {
            return;
        }
        const selected = this.isSelected(account);
        if (!selected && this.isModeDisabled(account)) {
            return;
        }
        if (config.many2one) {
            await this.props.record.update({
                [config.accountField]: selected ? false : [account.id, account.name],
            });
        } else {
            await this.props.record.data[config.accountField].addAndRemove(
                selected ? { remove: [account.id] } : { add: [account.id] }
            );
        }
        const hasAny = config.many2one
            ? !!this.props.record.data[config.accountField]
            : this.props.record.data[config.accountField].currentIds.length > 0;
        await this.props.record.update({ [config.boolField]: hasAny });
        await this._syncHasSelectedPlatform();
    }

    async _syncHasSelectedPlatform() {
        const anySelected = postPlatformAccountFields.getEntries().some(([, config]) => {
            const fieldValue = this.props.record.data[config.accountField];
            return config.many2one ? !!fieldValue : !!fieldValue && fieldValue.currentIds.length > 0;
        });
        if (anySelected !== this.props.record.data.has_selected_platform) {
            await this.props.record.update({ has_selected_platform: anySelected });
        }
    }
}

registry.category("view_widgets").add("post_platform_accounts", {
    component: PostPlatformAccounts,
});
