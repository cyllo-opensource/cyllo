/** @odoo-module **/
import { Dialog } from "@web/core/dialog/dialog";
import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
const { Component, useState, onWillStart } = owl;

export class AlertConfigurationDialog extends Component {
    static template = "cyllo_analytics.AlertConfigurationDialog";
    static components = { Dialog, AutoComplete };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.user = useService("user");

        const item = this.props.item;
        const axisIds = item.axis_ids || [];

        // Collect measure axes
        const measureAxes = axisIds.filter(a => a.type === 'measure');
        // Collect dimension axis (X-axis)
        const dimensionAxis = axisIds.find(a => a.type === 'dimension') || null;

        // Expose for template getters
        this._measureAxes = measureAxes;
        this._dimensionAxis = dimensionAxis;

        this.state = useState({
            alertId: null,
            name: `${item.name} Alert`,
            send_email: false,
            screen_notification: true,
            userName: this.user.name,
            notify_users: [], // Selected users: { id, name }

            // One row per measure: { alias, label, enabled, condition, value }
            measureConditions: measureAxes.map(m => ({
                alias: m.alias || m.name || '',
                label: m.label || m.name || m.alias || '',
                enabled: false,
                condition: 'gt',
                value: 0,
            })),

            // Dimension filter
            dimension_filter: false,
            dimension_alias: dimensionAxis ? (dimensionAxis.alias || dimensionAxis.name || '') : '',
            dimension_label: dimensionAxis ? (dimensionAxis.name || '') : '',
            dimension_value: '',
            dimensionValues: this.props.dimensionValues || [],
        });

        onWillStart(async () => {
            const fields = [
                "name", "send_email", "screen_notification",
                "condition_ids", "dimension_filter",
                "dimension_alias", "dimension_label", "dimension_value",
                "notify_user_ids"
            ];
            const existing = await this.orm.searchRead("dashboard.alert", [
                ["sheet_id", "=", item.id],
                ["user_id", "=", this.user.userId],
            ], fields);

            if (existing.length > 0) {
                const alert = existing[0];
                this.state.alertId = alert.id;
                this.state.name = alert.name;
                this.state.send_email = alert.send_email;
                this.state.screen_notification = alert.screen_notification;
                this.state.dimension_filter = alert.dimension_filter || false;
                this.state.dimension_alias = alert.dimension_alias || this.state.dimension_alias;
                this.state.dimension_label = alert.dimension_label || this.state.dimension_label;
                this.state.dimension_value = alert.dimension_value || '';

                if (alert.notify_user_ids && alert.notify_user_ids.length > 0) {
                    this.state.notify_users = await this.orm.read(
                        "res.users", alert.notify_user_ids, ["id", "display_name"]
                    );
                }

                // If saved condition_ids exist, re-enable the matching measure rows
                if (alert.condition_ids && alert.condition_ids.length > 0) {
                    const condRecs = await this.orm.read(
                        "dashboard.alert.condition",
                        alert.condition_ids,
                        ["measure_alias", "measure_label", "condition", "value"]
                    );
                    condRecs.forEach(rec => {
                        const row = this.state.measureConditions.find(
                            r => r.alias === rec.measure_alias
                        );
                        if (row) {
                            row.enabled = true;
                            row.condition = rec.condition;
                            row.value = rec.value;
                        }
                    });
                }
            }
        });
    }

    /** True when the chart has at least one measure axis */
    get hasMeasures() {
        return this._measureAxes.length > 0;
    }

    /** True when the chart has a dimension (X-axis) */
    get hasDimension() {
        return this._dimensionAxis !== null;
    }

    /** Safe dimension name string for template display */
    get dimensionAxisName() {
        return this._dimensionAxis ? (this._dimensionAxis.name || 'Dimension') : '';
    }

    /** Condition options – text only, no symbols */
    get conditionOptions() {
        return [
            { value: 'gt', label: _t('Greater Than') },
            { value: 'lt', label: _t('Less Than') },
            { value: 'eq', label: _t('Equals') },
            { value: 'ge', label: _t('Greater or Equal') },
            { value: 'le', label: _t('Less or Equal') },
        ];
    }

    toggleMeasure(index) {
        this.state.measureConditions[index].enabled =
            !this.state.measureConditions[index].enabled;
    }

    async onSave() {
        try {
            const enabled = this.state.measureConditions.filter(r => r.enabled);

            if (enabled.length === 0) {
                this.notification.add(
                    "Please enable at least one measure condition before saving.",
                    { type: "warning" }
                );
                return;
            }

            const vals = {
                name: this.state.name,
                sheet_id: this.props.item.id,
                send_email: this.state.send_email,
                screen_notification: this.state.screen_notification,
                user_id: this.user.userId,
                dimension_filter: this.state.dimension_filter,
                dimension_alias: this.state.dimension_alias,
                dimension_label: this.state.dimension_label,
                dimension_value: this.state.dimension_filter
                    ? this.state.dimension_value : '',
                // Replace all existing condition rows
                condition_ids: [
                    [5, 0, 0],   // unlink all previous
                    ...enabled.map(r => [0, 0, {
                        measure_alias: r.alias,
                        measure_label: r.label,
                        condition: r.condition,
                        value: r.value,
                    }]),
                ],
                notify_user_ids: [[6, 0, this.state.notify_users.map(u => u.id)]],
            };

            if (this.state.alertId) {
                await this.orm.write("dashboard.alert", [this.state.alertId], vals);
                this.notification.add("Alert updated successfully", { type: "success" });
            } else {
                await this.orm.create("dashboard.alert", [vals]);
                this.notification.add("Alert created successfully", { type: "success" });
            }
            this.props.close();
        } catch (error) {
            console.error("Alert save error:", error);
            this.notification.add(
                "Could not save alert: " + (error.message || "Unknown error"),
                { type: "danger" }
            );
        }
    }

    async onDelete() {
        if (this.state.alertId) {
            await this.orm.unlink("dashboard.alert", [this.state.alertId]);
            this.notification.add("Alert deleted successfully", { type: "success" });
            this.props.close();
        }
    }

    get dimensionSources() {
        return [
            {
                placeholder: "Search or select a value...",
                options: (str) => {
                    const values = (this.state.dimensionValues || []).filter(v => v !== null && v !== undefined);
                    const searchStr = (str || "").toLowerCase();
                    return values
                        .filter(v => String(v).toLowerCase().includes(searchStr))
                        .map(v => ({ label: String(v), value: v }));
                }
            }
        ];
    }

    onDimensionSelect(selected) {
        this.state.dimension_value = selected.value;
    }

    get userSources() {
        return [{
            placeholder: "Search for users...",
            options: async (str) => {
                const users = await this.orm.searchRead(
                    "res.users", 
                    [['name', 'ilike', str], ['active', '=', true]], 
                    ["id", "display_name"], 
                    { limit: 10 }
                );
                return users.map(u => ({ label: u.display_name, value: u.id }));
            }
        }];
    }

    onUserSelect(selected) {
        if (!this.state.notify_users.find(u => u.id === selected.value)) {
            this.state.notify_users.push({ 
                id: selected.value, 
                display_name: selected.label 
            });
        }
    }

    removeUser(userId) {
        this.state.notify_users = this.state.notify_users.filter(u => u.id !== userId);
    }

    conditionSources(row) {
        return [{
            options: (str) => {
                const searchStr = (str || "").toLowerCase();
                return this.conditionOptions
                    .filter(opt => opt.label.toLowerCase().includes(searchStr))
                    .map(opt => ({
                        label: opt.label,
                        value: opt.value,
                        isSelected: row.condition === opt.value
                    }));
            }
        }];
    }

    onConditionSelect(row, selected) {
        row.condition = selected.value;
    }

    /** Display label for the current condition in a row */
    getConditionLabel(row) {
        const opt = this.conditionOptions.find(o => o.value === row.condition);
        return opt ? opt.label : "Select Condition...";
    }
}
