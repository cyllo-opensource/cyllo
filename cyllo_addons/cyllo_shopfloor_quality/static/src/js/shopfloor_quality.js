/** @odoo-module **/
/**
 * cyllo_shopfloor_quality
 *
 * Patches the ShopFloor screen to show a Quality Check button on MO cards
 * that are ready to close (production_state == 'to_close') or completed ('done')
 * and have quality checks configured. Clicking opens the custom QualityCheck component (sidebar).
 * Also adds a dropdown option to create a Quality Alert for these MOs.
 */

import { patch } from "@web/core/utils/patch";
import { useState, onWillDestroy } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { QualityCheck } from "@cyllo_quality/js/components/quality_check/qualityCheck";

const ShopFloorScreen = registry.category("actions").get("shopfloor_screen");

ShopFloorScreen.components = {
    ...ShopFloorScreen.components,
    QualityCheck,
};

patch(ShopFloorScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.qcState = useState({
            byMo: {},
            showSidebar: false,
            activeMoId: null,
            activeCheckIds: [],
        });

        if (this.env.bus) {
            const onReloadQc = () => {
                this._loadQualityState();
            };

            this.env.bus.addEventListener("RELOAD_QC_DATA", onReloadQc);

            onWillDestroy(() => {
                this.env.bus.removeEventListener("RELOAD_QC_DATA", onReloadQc);
            });
        }
    },

    async loadWorkOrders() {
        await super.loadWorkOrders(...arguments);
        await this._loadQualityState();
    },

    async _loadQualityState() {
        const ids = this.state.groupedWorkOrders
            .map(g => g.production_id)
            .filter(Boolean);
        if (!ids.length) return;

        const rows = await this.orm.searchRead(
            "mrp.production",
            [["id", "in", ids]],
            ["id", "is_quality_check", "qc_count", "qc_checked_count", "quality_check_ids"]
        );

        const map = {};
        for (const r of rows) {
            map[r.id] = {
                is_quality_check: r.is_quality_check,
                qc_count: r.qc_count,
                qc_checked_count: r.qc_checked_count,
                quality_check_ids: r.quality_check_ids || [],
            };
        }
        this.qcState.byMo = map;
    },

    async openQualityCheck(productionId, ev) {
        if (ev) ev.stopPropagation();

        const qc = this.qcState.byMo[productionId];
        if (!qc) return;

        let checkIds = qc.quality_check_ids;

        if (!checkIds.length) {
            try {
                await this.orm.call(
                    "mrp.production", "action_quality_check", [[productionId]]
                );
                await this._loadQualityState();

                const updated = this.qcState.byMo[productionId];
                if (updated) {
                    checkIds = updated.quality_check_ids;
                }
            } catch (err) {
                this.env.services.notification.add(
                    err.message || "Could not create quality checks.",
                    { type: "danger" }
                );
                return;
            }
        }

        this.qcState.activeMoId = productionId;
        this.qcState.activeCheckIds = checkIds;
        this.qcState.showSidebar = true;

        setTimeout(() => {
            if (this.env.bus) {
                this.env.bus.trigger("GET_QUALITY_ACTIONS");
            }
        }, 100);
    },

    /**
     * Opens the Quality Alert form view in a new dialog
     */
    async actionCreateQualityAlert(productionId) {
        if (!productionId) return;

        const moData = await this.orm.read(
            "mrp.production",
            [productionId],
            ["product_id"]
        );

        let defaultContext = {};
        if (moData && moData.length > 0) {
            defaultContext = {
                default_product_id: moData[0].product_id ? moData[0].product_id[0] : false,
            };
        }

        this.action.doAction({
            name: "Quality Alert",
            type: "ir.actions.act_window",
            res_model: "quality.alert",
            views: [[false, "form"]],
            target: "new",
            context: defaultContext,
        });
    }
});
