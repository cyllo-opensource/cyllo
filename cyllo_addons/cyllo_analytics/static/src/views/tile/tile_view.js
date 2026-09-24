/** @odoo-module **/
import { _lt } from "@web/core/l10n/translation";
import { RelationalModel } from "@web/model/relational_model/relational_model";
import { registry } from "@web/core/registry";
import { TileRenderer } from "./tile_renderer";
import { TileController } from "./tile_controller";
import { TileArchParser } from "./tile_arch_parser";

export const tileView = {
    type: "tile", // Type of the view
    display_name: _lt("Tile"), // Display name of the view
    icon: "fa fa-dashboard", // Icon for the view
    multiRecord: true, // Indicates whether the view supports multiple records
    Controller: TileController, // Controller component for the view
    Renderer: TileRenderer, // Renderer component for the view
    ArchParser: TileArchParser, // Arch parser component for the view
    Model: RelationalModel, // Model used for the view
    limit: 80, // Default limit for records to be displayed in the view

    /**
     * Generate and return props (properties) for the "tile" view.
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
registry.category("views").add("tile", tileView);