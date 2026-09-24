/** @odoo-module **/
import { _lt } from "@web/core/l10n/translation";
import { RelationalModel } from "@web/model/relational_model/relational_model";
import { registry } from "@web/core/registry";
import { GridRenderer } from "./grid_renderer";
import { GridController } from "./grid_controller";
import { GridArchParser } from "./grid_arch_parser";
import { GridRelationalModel } from "./grid_relational_model";
export const gridView = {
    searchMenuTypes: ["filter", "comparison", "favorite"],
    type: "grid",
    display_name: _lt("Grid"),
    icon: "ri-align-item-left-line",
    multiRecord: true,
    Controller: GridController,
    Renderer: GridRenderer,
    ArchParser: GridArchParser,
    Model: GridRelationalModel,
    /**
     * Function that returns the props for the grid view.
     * @param {object} genericProps - Generic properties of the view.
     * @param {object} view - The view object.
     * @returns {object} Props for the grid view.
     */
    props: (genericProps, view) => {
        const {
            ArchParser,
            Model,
            Renderer
        } = view;
        const {
            arch,
            relatedModels,
            resModel
        } = genericProps;
        const archInfo = new ArchParser().parse(arch, relatedModels, resModel);
        return {
            ...genericProps,
            archInfo,
            Model: view.Model,
            Renderer,
        };
    }
};
// Register the grid view configuration
registry.category("views").add("grid", gridView);