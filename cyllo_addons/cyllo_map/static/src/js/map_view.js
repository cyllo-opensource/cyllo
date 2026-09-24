/** @odoo-module */

import { registry } from "@web/core/registry";
import { MapViewRenderer } from "./map_view_renderer.js";
import { MapViewController } from "./map_view_controller.js";
import { MapviewArchParser } from "./map_view_arch_parser.js";
import { RelationalModel } from "@web/model/relational_model/relational_model";

export const Mapview = {
    type: "map_view",
    display_name: "Map",
    icon: "ri-map-pin-line",
    multiRecord: true,
    Controller: MapViewController,
    Renderer: MapViewRenderer,
    Model: RelationalModel,
    ArchParser: MapviewArchParser,
    buttonTemplate: "web.ListView.Buttons",
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
registry.category("views").add("map_view", Mapview);
