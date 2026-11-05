/** @odoo-module **/
/**
 * Chart-suggestion cards as a chat widget, so a "Generate charts" turn is saved
 * to the chat history (cyllo_ai persists host widgets that report `onReady`) and
 * comes back with working Apply buttons when the conversation is reopened.
 *
 * Also patches the chat header's offer button: on the analytics sheet it adds
 * the suggestions to the CURRENT conversation instead of starting a new one.
 */
import { Component, onMounted } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { ChatBot } from "@cyllo_ai/chatbot/chatbot";

export const CHART_OFFER_KEY = "gen_charts";

export class ChartSuggestionsCard extends Component {
    static template = "cyllo_ai_analytics.ChartSuggestionsCard";
    static props = {
        suggestions: { type: Array, optional: true },
        sheetId: { type: [Number, Boolean], optional: true },
        sheetName: { type: String, optional: true },
        onReady: { type: Function, optional: true },
    };

    setup() {
        this.notification = useService("notification");
        onMounted(() => {
            const suggestions = this.props.suggestions || [];
            this.props.onReady?.({
                responseText: suggestions.length
                    ? suggestions.map((s) => `- ${s.title}`).join("\n")
                    : _t("No useful chart pairings were found."),
                props: {
                    suggestions,
                    sheetId: this.props.sheetId || false,
                    sheetName: this.props.sheetName || "",
                },
            });
        });
    }

    /** Apply a card to the open sheet, or explain why it can't be applied. */
    onApply(suggestion) {
        if (!document.body.classList.contains("cy-sheet-active")) {
            this.notification.add(
                _t("Open the analytics sheet these charts were suggested for to apply them."),
                { type: "warning" },
            );
            return;
        }
        this.env.bus.trigger("CY_AI:APPLY_SUGGESTION", {
            suggestion,
            sheetId: this.props.sheetId || false,
            sheetName: this.props.sheetName || "",
        });
    }
}

registry.category("cyllo_ai.chat_widgets").add("chart_suggestions", ChartSuggestionsCard);

patch(ChatBot.prototype, {
    /** Add chart suggestions to the open conversation instead of replacing it. */
    onHeaderSuggest() {
        if (this.state.offer?.key === CHART_OFFER_KEY) {
            this.onOfferClick();
            return;
        }
        return super.onHeaderSuggest(...arguments);
    },
});
