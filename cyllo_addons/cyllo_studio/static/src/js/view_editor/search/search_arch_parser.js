/** @odoo-module **/

/**
 * Extended SearchArchParser patch for Studio enhancements
 *
 * This patch adds support for handling:
 * - <studio> nodes in search views
 * - Custom field, filter, group, and separator parsing
 * - Default values and context handling for filters
 * - Compatibility fixes for counters and category sections
 */

import { patch } from "@web/core/utils/patch";
import { SearchArchParser } from "@web/search/search_arch_parser";
import { makeContext } from "@web/core/context";
import { archParseBoolean } from "@web/views/utils";
import { _t } from "@web/core/l10n/translation";
import { evaluateExpr, evaluateBooleanExpr } from "@web/core/py_js/py";
import { visitXML } from "@web/core/utils/xml";
import { DEFAULT_INTERVAL, DEFAULT_PERIOD } from "@web/search/utils/dates";

const ALL = _t("All");
const DEFAULT_LIMIT = 200;

/**
 * Extracts the group_by field names from a context string.
 *
 * @param {string} context - Context string from XML attributes
 * @returns {string[]} Array of group_by fields
 */
function getContextGroubBy(context) {
    try {
        return makeContext([context]).group_by.split(":");
    } catch {
        return [];
    }
}

/**
 * Simplifies a filter or group type to a reduced form.
 *
 * @param {string} type - Original type string
 * @returns {string} Reduced type ('filter', 'groupBy', or original)
 */
function reduceType(type) {
    if (type === "dateFilter") {
        return "filter";
    }
    if (type === "dateGroupBy") {
        return "groupBy";
    }
    return type;
}

/**
     * Main parse method to visit XML nodes and build search metadata.
     *
     * @returns {Object} Parsed search info (labels, preSearchItems, searchPanelInfo, sections)
     */
patch(SearchArchParser.prototype, {
    parse() {
        visitXML(this.arch, (node, visitChildren) => {
            switch (node.tagName) {
                case "search":
                    this.visitSearch(node, visitChildren);
                    break;
                case "searchpanel":
                    return this.visitSearchPanel(node);
                case "group":
                    this.visitGroup(node, visitChildren);
                    break;
                case "separator":
                    this.visitSeparator(node);
                    break;
                case "field":
                    this.visitField(node);
                    break;
                case "filter":
                    this.visitFilter(node);
                    break;
                case "studio":
                    this.visitStudio(node);
                    break;
            }
        });

        return {
            labels: this.labels,
            preSearchItems: this.preSearchItems,
            searchPanelInfo: this.searchPanelInfo,
            sections: this.sections,
        };
    },

    /**
     * Handles <studio> node parsing.
     * Sets default filter and group_by attributes if provided.
     *
     * @param {Element} node - XML node
     */
    visitStudio(node) {
        if (node.hasAttribute("filter")) {
            this.searchPanelInfo.filter = node.getAttribute("filter");
        }
        if (node.hasAttribute("group_by")) {
            this.searchPanelInfo.groupBy = node.getAttribute("group_by");
        }
    },

    /**
     * Parses <field> nodes in search views.
     * Extracts attributes, default values, context, and operator info.
     *
     * @param {Element} node - XML node
     */
    visitField(node) {
        this.pushGroup("field");
        const preField = { type: "field" };
        preField.cyXpath = node.getAttribute("cy-xpath");
        if (node.hasAttribute("striped")) {
            preField.striped = archParseBoolean(node.getAttribute("striped"));
        }
        if (node.hasAttribute("groups")) {
            preField.groups = node.getAttribute("groups");
        }
        if (node.hasAttribute("invisible")) {
            preField.invisible = node.getAttribute("invisible");
        }
        if (node.hasAttribute("domain")) {
            preField.domain = node.getAttribute("domain");
        }
        if (node.hasAttribute("filter_domain")) {
            preField.filterDomain = node.getAttribute("filter_domain");
        } else if (node.hasAttribute("operator")) {
            preField.operator = node.getAttribute("operator");
        }
        if (node.hasAttribute("context")) {
            preField.context = node.getAttribute("context");
        }
        if (node.hasAttribute("name")) {
            const name = node.getAttribute("name");
            const fieldType = this.fields[name].type;
            preField.fieldName = name;
            preField.fieldType = fieldType;
            if (fieldType !== "properties" && name in this.searchDefaults) {
                preField.isDefault = true;
                let value = this.searchDefaults[name];
                value = Array.isArray(value) ? value[0] : value;
                let operator = preField.operator;
                if (!operator) {
                    let type = fieldType;
                    if (node.hasAttribute("widget")) {
                        type = node.getAttribute("widget");
                    }
                    // Note: many2one as a default filter will have a
                    // numeric value instead of a string => we want "="
                    // instead of "ilike".
                    if (["char", "html", "many2many", "one2many", "text"].includes(type)) {
                        operator = "ilike";
                    } else {
                        operator = "=";
                    }
                }
                preField.defaultRank = -10;
                const { selection, context, relation } = this.fields[name];
                preField.defaultAutocompleteValue = { label: `${value}`, operator, value };
                if (fieldType === "selection") {
                    const option = selection.find((sel) => sel[0] === value);
                    if (!option) {
                        throw Error();
                    }
                    preField.defaultAutocompleteValue.label = option[1];
                } else if (fieldType === "many2one") {
                    this.labels.push((orm) => {
                        return orm
                            .call(relation, "read", [value, ["display_name"]], { context })
                            .then((results) => {
                                preField.defaultAutocompleteValue.label =
                                    results[0]["display_name"];
                            });
                    });
                }
            }
        } else {
            throw Error(); //but normally this should have caught earlier with view arch validation server side
        }
        if (node.hasAttribute("string")) {
            preField.description = node.getAttribute("string");
        } else if (preField.fieldName) {
            preField.description = this.fields[preField.fieldName].string;
        } else {
            preField.description = "Ω";
        }
        this.currentGroup.push(preField);
    },

     /**
     * Parses <filter> nodes in search views.
     * Handles date filters, groupBy, domain, visibility, and defaults.
     *
     * @param {Element} node - XML node
     */
    visitFilter(node) {
        const preSearchItem = { type: "filter" };
        preSearchItem.cyXpath = node.getAttribute("cy-xpath");
        if (node.hasAttribute("striped")) {
            preSearchItem.striped = archParseBoolean(node.getAttribute("striped"));
        }
        if (node.hasAttribute("groups")) {
            preSearchItem.groups = node.getAttribute("groups");
        }
        if (node.hasAttribute("context")) {
            const context = node.getAttribute("context");
            const [fieldName, defaultInterval] = getContextGroubBy(context);
            const groupByField = this.fields[fieldName];
            if (groupByField) {
                preSearchItem.type = "groupBy";
                preSearchItem.fieldName = fieldName;
                preSearchItem.fieldType = groupByField.type;
                if (["date", "datetime"].includes(groupByField.type)) {
                    preSearchItem.type = "dateGroupBy";
                    preSearchItem.defaultIntervalId = defaultInterval || DEFAULT_INTERVAL;
                }
            } else {
                preSearchItem.context = context;
            }
        }
        if (reduceType(preSearchItem.type) !== this.currentTag) {
            this.pushGroup(reduceType(preSearchItem.type));
        }
        if (preSearchItem.type === "filter") {
            if (node.hasAttribute("date")) {
                const fieldName = node.getAttribute("date");
                preSearchItem.type = "dateFilter";
                preSearchItem.fieldName = fieldName;
                preSearchItem.fieldType = this.fields[fieldName].type;
                preSearchItem.defaultGeneratorIds = [DEFAULT_PERIOD];
                if (node.hasAttribute("default_period")) {
                    preSearchItem.defaultGeneratorIds = node
                        .getAttribute("default_period")
                        .split(",");
                }
            } else {
                let stringRepr = "[]";
                if (node.hasAttribute("domain")) {
                    stringRepr = node.getAttribute("domain");
                }
                preSearchItem.domain = stringRepr;
            }
        }
        if (node.hasAttribute("invisible")) {
            preSearchItem.invisible = node.getAttribute("invisible");
            const fieldName = preSearchItem.fieldName;
            if (fieldName && !this.fields[fieldName]) {
                // In some case when a field is limited to specific groups
                // on the model, we need to ensure to discard related filter
                // as it may still be present in the view (in 'invisible' state)
                return;
            }
        }
        preSearchItem.groupNumber = this.groupNumber;
        if (node.hasAttribute("name")) {
            const name = node.getAttribute("name");
            preSearchItem.name = name;
            if (name in this.searchDefaults) {
                preSearchItem.isDefault = true;
                if (["groupBy", "dateGroupBy"].includes(preSearchItem.type)) {
                    const value = this.searchDefaults[name];
                    preSearchItem.defaultRank = typeof value === "number" ? value : 100;
                } else {
                    preSearchItem.defaultRank = -5;
                }
            }
        }
        if (node.hasAttribute("string")) {
            preSearchItem.description = node.getAttribute("string");
        } else if (preSearchItem.fieldName) {
            preSearchItem.description = this.fields[preSearchItem.fieldName].string;
        } else if (node.hasAttribute("help")) {
            preSearchItem.description = node.getAttribute("help");
        } else if (node.hasAttribute("name")) {
            preSearchItem.description = node.getAttribute("name");
        } else {
            preSearchItem.description = "Ω";
        }
        this.currentGroup.push(preSearchItem);
    },

    /**
     * Parses <searchpanel> nodes and constructs sections for UI.
     * Handles categories, filters, counters, hierarchy, and limits.
     *
     * @param {Element} searchPanelNode
     * @returns {boolean} False if no children should be visited further
     */
    visitSearchPanel(searchPanelNode) {
        let hasCategoryWithCounters = false;
        let hasFilterWithDomain = false;
        let nextSectionId = 1;
        const showInvisibleSearch = JSON.parse(sessionStorage.getItem("showInvisibleSearch")) || false;
        if (searchPanelNode.hasAttribute("class")) {
            this.searchPanelInfo.className = searchPanelNode.getAttribute("class");
        }
        if (searchPanelNode.hasAttribute("view_types")) {
            this.searchPanelInfo.viewTypes = searchPanelNode.getAttribute("view_types").split(",");
        }

        if (searchPanelNode.hasAttribute("cy-xpath")) {
            this.searchPanelInfo.cyXpath = searchPanelNode.getAttribute("cy-xpath");
        }
        if (searchPanelNode.hasAttribute("groups")) {
            this.searchPanelInfo.groups = searchPanelNode.getAttribute("groups");
        }
        if (searchPanelNode.hasAttribute("isInvisible")) {
            this.searchPanelInfo.isInvisible = true;
            return
        }

        for (const node of searchPanelNode.children) {
            if (node.nodeType !== 1 || node.tagName !== "field") {
                continue;
            }
            if (
                node.getAttribute("invisible") === "True" ||
                node.getAttribute("invisible") === "1"
            ) {
                if(showInvisibleSearch){
                    node.setAttribute("striped","True")
                }
                else{
                    continue;
                }
            }
            const attrs = {};
            for (const attrName of node.getAttributeNames()) {
                attrs[attrName] = node.getAttribute(attrName);
            }
            const type = attrs.select === "multi" ? "filter" : "category";
            const section = {
                color: attrs.color || null,
                description: attrs.string || this.fields[attrs.name].string,
                enableCounters: evaluateBooleanExpr(attrs.enable_counters),
                expand: evaluateBooleanExpr(attrs.expand),
                fieldName: attrs.name,
                icon: attrs.icon || null,
                id: nextSectionId++,
                limit: evaluateExpr(attrs.limit || String(DEFAULT_LIMIT)),
                type,
                values: new Map(),
                striped: archParseBoolean(attrs.striped || "0"),
                accessGroups: attrs.groups || "",
                invisible: attrs.invisible,
                cyXpath: attrs['cy-xpath'],
            };
            if (type === "category") {
                section.activeValueId = this.searchPanelDefaults[attrs.name];
                section.icon = section.icon || "fa-folder";
                section.hierarchize = evaluateBooleanExpr(attrs.hierarchize || "1");
                section.values.set(false, {
                    childrenIds: [],
                    display_name: ALL.toString(),
                    id: false,
                    bold: true,
                    parentId: false,
                });
                hasCategoryWithCounters = hasCategoryWithCounters || section.enableCounters;
            } else {
                section.domain = attrs.domain || "[]";
                section.groupBy = attrs.groupby || null;
                section.icon = section.icon || "fa-filter";
                hasFilterWithDomain = hasFilterWithDomain || section.domain !== "[]";
            }
            this.sections.push([section.id, section]);
        }

        if (hasCategoryWithCounters && hasFilterWithDomain) {
            // If incompatibilities are found -> disables all category counters
            for (const section of this.sections) {
                if (section.type === "category") {
                    section.enableCounters = false;
                }
            }
            // ... and triggers a warning
            console.warn(
                "Warning: categories with counters are incompatible with filters having a domain attribute.",
                "All category counters have been disabled to avoid inconsistencies."
            );
        }
        return false;
    },
    /**
     * Parses <separator> nodes for search or group sections.
     *
     * @param {Element} node - XML node
     */
    visitSeparator(node) {
        const preSearchItem = { type: "filterSeparator" };
        preSearchItem.cyXpath = node.getAttribute("cy-xpath");
        if (this.currentTag === "groupBy") {
            preSearchItem.type = "groupSeparator"
        }
        this.currentGroup.push(preSearchItem)
        this.pushGroup();
    },
})
