/** @odoo-module **/
import { Component, onWillStart, reactive, useState, useSubEnv } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { deserializeDateTime, formatDateTime } from "@web/core/l10n/dates";
import { Dialog } from "@web/core/dialog/dialog";
import { FormController } from "@web/views/form/form_controller";
import { STATIC_ACTIONS_GROUP_NUMBER } from "@web/search/action_menus/action_menus";
import { CogMenuItem } from "@cyllo_base/js/cog_menu_item";

const BRIEFING_MODELS = ["res.partner", "crm.lead", "project.project"];
const CACHE_MS = 10 * 60 * 1000;
const briefingStore = reactive({});

/**
 * Briefing for one record, shared by the chat card and the full view. A copy
 * younger than CACHE_MS is reused unless ``force`` asks for a fresh one.
 */
async function fetchBriefing(orm, resModel, resId, force = false) {
    const key = `${resModel}:${resId}`;
    const cached = briefingStore[key];
    if (!force && cached && Date.now() - cached.at < CACHE_MS) {
        return cached.brief;
    }
    const brief = await orm.call("cyllo.ai.briefing", "get_briefing", [resModel, resId]);
    briefingStore[key] = { brief, at: Date.now() };
    return brief;
}

/** Readable message of a failed briefing call. */
function briefingError(error) {
    return error.data?.message || error.message || _t("The briefing could not be built.");
}

/**
 * Record the briefing is about: the open form's record, or the project whose
 * tasks are being browsed (opening a project shows its tasks, not its form).
 */
function briefingTarget(env) {
    const record = env.config?.viewType === "form" && env.cylloAiFormRecord?.();
    if (record && BRIEFING_MODELS.includes(record.resModel)) {
        return { resModel: record.resModel, resId: record.resId, isNew: record.isNew };
    }
    const context = env.searchModel?.globalContext || {};
    if (
        env.searchModel?.resModel === "project.task" &&
        context.active_model === "project.project" &&
        context.default_project_id
    ) {
        return { resModel: "project.project", resId: context.default_project_id, isNew: false };
    }
    return null;
}

patch(FormController.prototype, {
    setup() {
        super.setup(...arguments);
        useSubEnv({ cylloAiFormRecord: () => this.model.root });
    },
});

/**
 * Briefing dialog: risks first, then key figures, the conversation and the
 * suggested next step. Every card and row opens the record it came from.
 * The last briefing per record is kept for a few minutes so following a link
 * and coming back does not regenerate it.
 */
export class CatchMeUpDialog extends Component {
    static template = "cyllo_ai.CatchMeUpDialog";
    static components = { Dialog };
    static props = {
        resModel: String,
        resId: Number,
        brief: { type: Object, optional: true },
        close: Function,
    };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({ loading: true, error: "", brief: null });
        onWillStart(() => {
            if (this.props.brief) {
                this.state.brief = this.props.brief;
                this.state.loading = false;
            } else {
                this.load(false);
            }
        });
    }

    get title() {
        return this.state.brief ? _t("Catch me up · %s", this.state.brief.title) : _t("Catch me up");
    }

    get moodLabel() {
        return {
            positive: _t("Positive"),
            neutral: _t("Neutral"),
            negative: _t("Unhappy"),
        }[this.state.brief?.mood];
    }

    /** Load the briefing; ``force`` (the Refresh button) skips the cache. */
    async load(force = true) {
        this.state.loading = true;
        this.state.error = "";
        try {
            this.state.brief = await fetchBriefing(
                this.orm, this.props.resModel, this.props.resId, force);
        } catch (error) {
            this.state.error = briefingError(error);
        } finally {
            this.state.loading = false;
        }
    }

    /** Open the record, or the filtered list, a card or row links to. */
    openLink(link) {
        if (!link || !link.res_model) {
            return;
        }
        this.props.close();
        if (link.res_id) {
            this.action.doAction({
                type: "ir.actions.act_window",
                res_model: link.res_model,
                res_id: link.res_id,
                views: [[false, "form"]],
                target: "current",
            });
        } else {
            this.action.doAction({
                type: "ir.actions.act_window",
                name: link.name,
                res_model: link.res_model,
                domain: link.domain,
                views: [[false, "list"], [false, "form"]],
                target: "current",
            });
        }
    }
}

/**
 * Compact briefing card posted in the AI chat: the summary, the risk count and
 * the next step. Clicking it opens the full briefing (CatchMeUpDialog).
 */
export class CatchMeUpChatCard extends Component {
    static template = "cyllo_ai.CatchMeUpChatCard";
    static props = {
        resModel: String,
        resId: Number,
        brief: { type: Object, optional: true },
        onReady: { type: Function, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.dialog = useService("dialog");
        this.store = useState(briefingStore);
        this.state = useState({ loading: false, error: "" });
        onWillStart(() => {
            if (!this.props.brief) {
                this.load();
            }
        });
    }

    get brief() {
        const fresh = this.store[`${this.props.resModel}:${this.props.resId}`]?.brief;
        return fresh || this.props.brief || null;
    }

    get savedAt() {
        const brief = this.brief;
        if (!brief || brief !== this.props.brief || !brief.generated_at) {
            return "";
        }
        return formatDateTime(deserializeDateTime(brief.generated_at));
    }

    get riskCounts() {
        const risks = this.brief?.risks || [];
        return {
            high: risks.filter((risk) => risk.severity === "high").length,
            medium: risks.filter((risk) => risk.severity !== "high").length,
        };
    }

    get moodLabel() {
        return {
            positive: _t("Positive"),
            neutral: _t("Neutral"),
            negative: _t("Unhappy"),
        }[this.brief?.mood];
    }

    /** Load the briefing (reusing a recent copy) for the card. */
    async load() {
        this.state.loading = !this.brief;
        this.state.error = "";
        try {
            const brief = await fetchBriefing(this.orm, this.props.resModel, this.props.resId);
            this.props.onReady?.({
                responseText: `${brief.title} (${brief.subtitle})\n\n${brief.summary}\n\n`
                    + _t("Next step: %s", brief.next_step),
                props: { resModel: this.props.resModel, resId: this.props.resId, brief },
            });
        } catch (error) {
            this.state.error = briefingError(error);
        } finally {
            this.state.loading = false;
        }
    }

    /** Open the full briefing view. */
    expand() {
        if (this.brief) {
            this.dialog.add(CatchMeUpDialog, {
                resModel: this.props.resModel,
                resId: this.props.resId,
                brief: this.brief,
            });
        }
    }

    onKeydown(ev) {
        if (ev.key === "Enter" || ev.key === " ") {
            ev.preventDefault();
            this.expand();
        }
    }
}

registry.category("cyllo_ai.chat_widgets").add("catch_me_up", CatchMeUpChatCard);

/** "Catch me up" entry in the form's top action bar. */
export class CatchMeUpCogItem extends Component {
    static template = "cyllo_ai.CatchMeUpCogItem";
    static components = { CogMenuItem };
    static props = {};

    setup() {
        this.dialog = useService("dialog");
        this.notification = useService("notification");
        this.rpc = useService("rpc");
    }

    /** True when the AI chat is configured and shown, so the card can go there. */
    async chatAvailable() {
        try {
            return (await this.rpc("/cyllo/get_ai_widget_enabled")) === "1";
        } catch {
            return false;
        }
    }

    async onClick() {
        const target = briefingTarget(this.env);
        if (!target) {
            return;
        }
        if (target.isNew) {
            this.notification.add(_t("Save the record first to get a briefing."), {
                type: "warning",
            });
            return;
        }
        const props = { resModel: target.resModel, resId: target.resId };
        if (await this.chatAvailable()) {
            this.env.bus.trigger("CY_AI:PUSH_MESSAGE", {
                open: true,
                persist: true,
                userText: _t("Catch me up"),
                intro: _t("Here's where things stand:"),
                widget: { key: "catch_me_up", props },
            });
        } else {
            this.dialog.add(CatchMeUpDialog, props);
        }
    }
}

registry.category("cogMenu").add(
    "cyllo-ai-catch-me-up",
    {
        Component: CatchMeUpCogItem,
        groupNumber: STATIC_ACTIONS_GROUP_NUMBER,
        isDisplayed: (env) => !env.inDialog && Boolean(briefingTarget(env)),
    },
    { sequence: 5 }
);
