/** @odoo-module */
import { patch } from "@web/core/utils/patch";
import { PivotArchParser } from "@web/views/pivot/pivot_arch_parser";
import { visitXML } from "@web/core/utils/xml";
import { archParseBoolean } from "@web/views/utils";

patch(PivotArchParser.prototype, {
     parse(arch) {
        const archInfo = {
            activeMeasures: [], // store the defined active measures
            colGroupBys: [], // store the defined group_by used on cols
            defaultOrder: null,
            fieldAttrs: {},
            rowGroupBys: [], // store the defined group_by used on rows
            widgets: {}, // wigdets defined in the arch
        };

        visitXML(arch, (node) => {
            switch (node.tagName) {
                case "pivot": {
                    if (node.hasAttribute("disable_linking")) {
                        archInfo.disableLinking = archParseBoolean(
                            node.getAttribute("disable_linking")
                        );
                    }
                    if (node.hasAttribute("sticky")) {
                        archInfo.sticky = archParseBoolean(
                            node.getAttribute("sticky")
                        );
                    }
                    if (node.hasAttribute("default_order")) {
                        archInfo.defaultOrder = node.getAttribute("default_order");
                    }
                    if (node.hasAttribute("string")) {
                        archInfo.title = node.getAttribute("string");
                    }
                    if (node.hasAttribute("display_quantity")) {
                        archInfo.displayQuantity = archParseBoolean(
                            node.getAttribute("display_quantity")
                        );
                    }
                    break;
                }
                case "field": {
                    let fieldName = node.getAttribute("name"); // exists (rng validation)

                    archInfo.fieldAttrs[fieldName] = {};
                    if (node.hasAttribute("string")) {
                        archInfo.fieldAttrs[fieldName].string = node.getAttribute("string");
                    }
                    if (
                        node.getAttribute("invisible") === "True" ||
                        node.getAttribute("invisible") === "1"
                    ) {
                        archInfo.fieldAttrs[fieldName].isInvisible = true;
                        break;
                    }

                    if (node.hasAttribute("interval")) {
                        fieldName += ":" + node.getAttribute("interval");
                    }
                    if (node.hasAttribute("widget")) {
                        archInfo.widgets[fieldName] = node.getAttribute("widget");
                    }
                    if (node.getAttribute("type") === "measure" || node.hasAttribute("operator")) {
                        archInfo.activeMeasures.push(fieldName);
                    }
                    if (node.getAttribute("type") === "col") {
                        archInfo.colGroupBys.push(fieldName);
                    }
                    if (node.getAttribute("type") === "row") {
                        archInfo.rowGroupBys.push(fieldName);
                    }
                    break;
                }
            }
            if (document.querySelector('.cy_sticky_first_child')) {
                document.body.classList.add('conditional-style');
            }
        });

        return archInfo;
    }


});