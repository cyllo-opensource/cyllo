/** @odoo-module **/

import { ChannelSelector } from "@mail/discuss/core/web/channel_selector";
import { cleanTerm } from "@mail/utils/common/format";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(ChannelSelector.prototype, {
    async fetchSuggestions() {
        const cleanedTerm = cleanTerm(this.state.value);
        if (cleanedTerm) {
            if (this.props.category.id === "channels") {
                const domain = [
                    ["channel_type", "=", "channel"],
                    ["name", "ilike", cleanedTerm],
                ];
                const fields = ["name"];
                const results = await this.sequential(async () => {
                    this.state.navigableListProps.isLoading = true;
                    const res = await this.orm.searchRead("discuss.channel", domain, fields, {
                        limit: 10,
                    });
                    this.state.navigableListProps.isLoading = false;
                    return res;
                });
                if (!results) {
                    this.state.navigableListProps.options = [];
                    return;
                }
                const choices = results.map((channel) => {
                    return {
                        channelId: channel.id,
                        classList: "o-discuss-ChannelSelector-suggestion",
                        label: channel.name,
                    };
                });
                choices.push({
                    channelId: "__create__",
                    classList: "o-discuss-ChannelSelector-suggestion",
                    label: cleanedTerm,
                });
                this.state.navigableListProps.options = choices;
                return;
            }
            if (this.props.category.id === "chats") {
                const results = await this.sequential(async () => {
                    this.state.navigableListProps.isLoading = true;
                    const res = await this.orm.call("res.partner", "im_search", [
                        cleanedTerm,
                        10,
                        this.state.selectedPartners,
                    ]);
                    this.state.navigableListProps.isLoading = false;
                    return res;
                });
                if (!results) {
                    this.state.navigableListProps.options = [];
                    return;
                }
                let suggestions = this.suggestionService
                    .sortPartnerSuggestions(results, cleanedTerm)
                    .map((data) => {
                        this.store.Persona.insert({ ...data, type: "partner" });
                        return {
                            classList: "o-discuss-ChannelSelector-suggestion",
                            label: data.name,
                            partner: data,
                        };
                    });
                if (this.store.self.name.includes(cleanedTerm)) {
                    suggestions.push({
                        classList: "o-discuss-ChannelSelector-suggestion",
                        label: this.store.self.name,
                        partner: this.store.self,
                    });
                }
                if (suggestions.length === 0) {
                    suggestions.push({
                        classList: "o-discuss-ChannelSelector-suggestion",
                        label: _t("No results found"),
                        unselectable: true,
                    });
                }
                if (this.store.facebook || this.store.instagram) {
                    var self = this;
                    suggestions = await Promise.all(suggestions.map(async (user) => {
                        if (user.partner) {
                            const partner = await this.orm.searchRead("res.partner", [
                                ["id", "=", user.partner.id]
                            ], []);
                            if ((self.store.facebook && !partner[0].unique_fb_number) || (self.store.instagram && !partner[0].unique_ig_number)) {
                                return null;
                            }
                        }
                        return user;
                    }));
                    suggestions = suggestions.filter(Boolean);
                }
                this.state.navigableListProps.options = suggestions;
                return;
            }
        }
        this.state.navigableListProps.options = [];
        return;
    },
    async onSelect(option) {
        super.onSelect(option);
        if (option.partner) {
            await this.orm.call("discuss.channel", "action_enable_social", ['',option.partner.id,this.store.facebook,this.store.instagram], {})
        }
    },
});