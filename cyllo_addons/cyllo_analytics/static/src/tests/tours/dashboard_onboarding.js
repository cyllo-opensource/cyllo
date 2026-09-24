/** @odoo-module **/
import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";
import { _t } from "@web/core/l10n/translation";

registry.category("web_tour.tours").add('cy_smart_dash_tour', {
    test: true,
    url: '/web#action=cy_analytic_dashboard',
    steps: () => [{
        trigger: ".cy-add-graph",
        content: _t("Click here to add a new Graph."),
        position: "left",
    },
    {
        trigger: "input[name='sheet_name']",
        content: _t("Add a name here."),
        position: "right",
    },
    {
        trigger: ".table_input_tags",
        content: _t("Search for a model or multiple models and select those tables here"),
        position: "right",
    },
    {
        trigger: ".dimensions .draggable-item",
        content: _t("Drag and Drop Dimension to the AXIS column to your right"),
        position: "right",
    },
    {
        trigger: ".measures .draggable-item",
        content: _t("Drag and Drop Measures to the other AXIS column to your right"),
        position: "right",
    },
    {
        trigger: ".save_button",
        content: _t("Click here to save sheet"),
        position: "bottom",
    },
]});