/** @odoo-module **/
import { _lt } from "@web/core/l10n/translation";
import { RelationalModel } from "@web/model/relational_model/relational_model";
import { registry } from "@web/core/registry";
import { WorkflowCardRenderer } from "./workflow_card_renderer";
import { WorkflowCardController } from "./workflow_card_controller";
import { WorkflowCardArchParser } from "./workflow_card_arch_parser";

export const workflowCardView = {
    type: "workflowCard", // Type of the view
    display_name: _lt("WorkflowCard"), // Display name of the view
    icon: "ri-flow-chart", // Icon for the view
    multiRecord: true, // Indicates whether the view supports multiple records
    Controller: WorkflowCardController, // Controller component for the view
    Renderer: WorkflowCardRenderer, // Renderer component for the view
    ArchParser: WorkflowCardArchParser, // Arch parser component for the view
    Model: RelationalModel, // Model used for the view
    limit: 80, // Default limit for records to be displayed in the view

    /**
     * Generate and return props (properties) for the "WorkAutoCardVied" view.
     * @param {Object} genericProps - Generic properties for the view.
     * @param {Object} view - Information about the view.
     * @returns {Object} - Props for the view, including parsed archInfo, Model, and Renderer.
     */

    props: (genericProps, view) => {
        const { ArchParser, Model, Renderer } = view;
        const { arch, relatedModels, resModel } = genericProps;
        // Parse the view's arch to obtain archInfo.
        const archInfo = new ArchParser().parse(arch, relatedModels, resModel);
        return {
            ...genericProps,
            archInfo,
            Model,
            Renderer,
        };
    }
};
registry.category("views").add("workflowCard", workflowCardView);