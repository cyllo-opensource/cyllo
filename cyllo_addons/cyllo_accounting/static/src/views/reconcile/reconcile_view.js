/** @odoo-module **/
import { _lt } from "@web/core/l10n/translation";
import { RelationalModel } from "@web/model/relational_model/relational_model";
import { registry } from "@web/core/registry";
import { ReconcileRenderer } from "./reconcile_renderer";
import { ReconcileController } from "./reconcile_controller";
import { ReconcileArchParser } from "./reconcile_arch_parser";
export const reconcileView = {
    type: "reconcile", // Type of the view
    display_name: _lt("Reconcile"), // Display name of the view
    icon: "ri-dashboard-line", // Icon for the view
    multiRecord: true, // Indicates whether the view supports multiple records
    Controller: ReconcileController, // Controller component for the view
    Renderer: ReconcileRenderer, // Renderer component for the view
    ArchParser: ReconcileArchParser, // Arch parser component for the view
    Model: RelationalModel, // Model used for the view
    limit: 80, // Default limit for records to be displayed in the view

    props: (genericProps, view) => {
        const { ArchParser } = view;
        const { arch, relatedModels, resModel } = genericProps;
        const archInfo = new ArchParser().parse(arch, relatedModels, resModel);

        return {
            ...genericProps,
            Model: view.Model,
            Renderer: view.Renderer,
            archInfo,
        };
    },

};
registry.category("views").add("reconcile", reconcileView);