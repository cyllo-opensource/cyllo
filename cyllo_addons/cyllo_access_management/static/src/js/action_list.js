/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";
import { FormController } from "@web/views/form/form_controller"
import { onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { ViewButton } from "@web/views/view_button/view_button";

patch(ViewButton.prototype, {
    get disabled() {
        if (session.is_profile_readonly) {
            return true;
        }
        return super.disabled;
    },
});

(async () => {
    try {
        const { Activity } = await import("@mail/core/web/activity");
        patch(Activity.prototype, {
            onClickMarkAsDone() {
                if (session.is_profile_readonly && this.props.data.user_id[0] !== session.uid) {
                    this.env.services.notification.add(_t("Access Denied: Readonly Profile"), { type: "danger" });
                    return;
                }
                return super.onClickMarkAsDone(...arguments);
            },

            unlink() {
                if (session.is_profile_readonly && this.props.data.user_id[0] !== session.uid) {
                    this.env.services.notification.add(_t("Access Denied: Readonly Profile"), { type: "danger" });
                    return;
                }
                return super.unlink(...arguments);
            },
        });
    } catch (e) {
        // mail module not installed, skip Activity patches
    }

    try {
        const { FollowerList } = await import("@mail/core/web/follower_list");
        patch(FollowerList.prototype, {
            onClickAddFollowers() {
                if (session.is_profile_readonly) {
                    this.env.services.notification.add(_t("Access Denied: Readonly Profile"), { type: "danger" });
                    return;
                }
                return super.onClickAddFollowers(...arguments);
            },
            async onClickEdit(ev, follower) {
                if (session.is_profile_readonly && follower !== this.props.thread.selfFollower) {
                    this.env.services.notification.add(_t("Access Denied: Readonly Profile"), { type: "danger" });
                    return;
                }
                return super.onClickEdit(...arguments);
            },
            async onClickRemove(ev, follower) {
                if (session.is_profile_readonly && follower !== this.props.thread.selfFollower) {
                    this.env.services.notification.add(_t("Access Denied: Readonly Profile"), { type: "danger" });
                    return;
                }
                return super.onClickRemove(...arguments);
            },
        });
    } catch (e) {
        // mail module not installed, skip FollowerList patches
    }
})();

(async () => {
    try {
        const { AccountPaymentField } = await import("@account/components/account_payment_field/account_payment_field");
        patch(AccountPaymentField.prototype, {
            async assignOutstandingCredit() {
                if (session.is_profile_readonly) {
                    this.env.services.notification.add(_t("Access Denied: Readonly Profile"), { type: "danger" });
                    return;
                }
                return super.assignOutstandingCredit(...arguments);
            },
        });
    } catch (e) {
        // account module not installed, skip AccountPaymentField patches
    }
})();

(async () => {
    try {
        const { AttendeeCalendarController } = await import("@calendar/views/attendee_calendar/attendee_calendar_controller");
        patch(AttendeeCalendarController.prototype, {
            onClickAddButton() {
                if (session.is_profile_readonly) {
                    this.env.services.notification.add(_t("Access Denied: Readonly Profile"), { type: "danger" });
                    return;
                }
                return super.onClickAddButton(...arguments);
            },
        });
    } catch (e) {
        // calendar module not installed, skip AttendeeCalendarController patches
    }
})();

patch(ListController.prototype, {
    setup() {
        super.setup(...arguments);
        const model = this.model.config.resModel;
        this.orm = useService('orm');
        onWillStart(async () => {
            this.profileFlags = await this.orm.call(
                "profile.management",
                "get_profile_flags",
                [], { model }
            )
            if (this.profileFlags.actions && this.profileFlags.actions.includes("export")) {
                this.env.config.hideExportAll = true;
            }
        });
    },

    get actionMenuItems() {
        const items = super.actionMenuItems;
        if (this.profileFlags.actions) {
            const actions = items.action.filter((item) => !this.profileFlags.actions.includes(item.key))
            items.action = actions
        }
        if (this.profileFlags.hide_actions) {
            delete items.action;
        }
        if (this.profileFlags.hide_print) {
            delete items.print;
        }
        return items;
    },

});

patch(FormController.prototype, {
    setup() {
        super.setup(...arguments);
        const model = this.model.config.resModel;
        onWillStart(async () => {
            this.profileFlags = await this.orm.call(
                "profile.management",
                "get_profile_flags",
                [], { model }
            )
        });
    },

    get actionMenuItems() {
        const items = super.actionMenuItems;
        if (this.profileFlags.actions) {
            const actions = items.action.filter((item) => !this.profileFlags.actions.includes(item.key))
            items.action = actions
        }
        if (this.profileFlags.hide_actions) {
            delete items.action;
        }
        if (this.profileFlags.hide_print) {
            delete items.print;
        }
        return items;
    },
});

const cogMenuRegistry = registry.category("cogMenu");
const exportAllItem = cogMenuRegistry.get("export-all-menu");
if (exportAllItem) {
    const originalIsDisplayed = exportAllItem.isDisplayed;
    exportAllItem.isDisplayed = async (env) => {
        if (env.config.hideExportAll) {
            return false;
        }
        return originalIsDisplayed ? await originalIsDisplayed(env) : true;
    };
}
