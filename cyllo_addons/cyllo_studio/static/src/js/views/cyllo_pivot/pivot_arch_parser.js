/** @odoo-module */

/**
 * Patch: PivotArchParser
 *
 * Extends the default Odoo PivotArchParser to include custom behavior
 * and extra metadata used in Cyllo Studio.
 *
 * Features:
 * 1. Tracks active measures, row and column groupings, and default ordering.
 * 2. Stores field-specific attributes like string labels and visibility.
 * 3. Collects widgets used in the pivot view.
 * 4. Adds support for cy-xpath attributes to store paths for UI interactions.
 * 5. Adds a CSS class 'conditional-style' to the body if a sticky pivot child exists.
 *
 * Purpose:
 * Enhances the pivot view architecture parsing to provide richer information
 * for Studio customization, drag-and-drop operations, and UI rendering.
 */
import {
    patch
} from "@web/core/utils/patch";
import {
    PivotArchParser
} from "@web/views/pivot/pivot_arch_parser";
import {
    visitXML
} from "@web/core/utils/xml";
import {
    archParseBoolean
} from "@web/views/utils";

patch(PivotArchParser.prototype, {
    parse(arch) {
        const archInfo = {
            activeMeasures: [], // store the defined active measures
            colGroupBys: [], // store the defined group_by used on cols
            defaultOrder: null,
            fieldAttrs: {},
            rowGroupBys: [], // store the defined group_by used on rows
            widgets: {}, // wigdets defined in the arch
            colPath: [],
            rowPath: [],
            measurePath: [],
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
                        if (node.getAttribute("cy-xpath")) {
                            const path = node.getAttribute("cy-xpath")
                            archInfo.measurePath.push(path);
                        }
                    }
                    if (node.getAttribute("type") === "col") {
                        archInfo.colGroupBys.push(fieldName);
                        if (node.getAttribute("cy-xpath")) {
                            const path = node.getAttribute("cy-xpath")
                            archInfo.colPath.push(path);
                        }
                    }
                    if (node.getAttribute("type") === "row") {
                        archInfo.rowGroupBys.push(fieldName);
                        if (node.getAttribute("cy-xpath")) {
                            const path = node.getAttribute("cy-xpath")
                            archInfo.rowPath.push(path);
                        }
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