/** @odoo-module **/
import { FormController } from "@web/views/form/form_controller";
import { formView } from '@web/views/form/form_view';
import { registry } from "@web/core/registry";
import { Component, useState, status } from "@odoo/owl";
import { useBus } from "@web/core/utils/hooks";
import { QualityCheck } from "@cyllo_quality/js/components/quality_check/qualityCheck";

export class QualityCheckFormView extends FormController {
    static template = "QualityCheckFormView";
    setup() {
        super.setup();
        useBus(this.env.bus, "RELOAD_QC_DATA", () => {
            if (status(this) !== "destroyed") {
                this.model.root.load();
            }
        });
    }

    async afterExecuteActionButton(clickParams) {
        if (status(this) === "destroyed") {
            return;
        }
        if (clickParams.name === 'action_quality_check') {
            this.env.bus.trigger("GET_QUALITY_ACTIONS")
            return super.afterExecuteActionButton(clickParams)
        } else return super.afterExecuteActionButton(clickParams)
    }

    get rootData() {
        return this.model.root
    }

    get qualityProps() {
        return {
            resId: this.rootData.resId,
            qualityCheckIds: this.rootData.data.quality_check_ids
                ? this.rootData.data.quality_check_ids._currentIds
                : (this.rootData.resId ? [this.rootData.resId] : [])
        }
    }
}
QualityCheckFormView.components = {
    ...FormController.components,
    QualityCheck
}

export const qualityCheckFormView = {
    ...formView,
    Controller: QualityCheckFormView,
};

registry.category("views").add("quality_check_view", qualityCheckFormView);