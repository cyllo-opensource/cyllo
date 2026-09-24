/** @odoo-module */

/**
 * CylloListArchParser
 *
 * Custom ArchParser for Odoo List (Tree) views used in Cyllo Studio.
 * Extends the default listView.ArchParser to provide enhanced parsing
 * capabilities for fields, widgets, buttons, groupBy nodes, and headers,
 * while maintaining session-based visibility control and custom attributes.
 *
 * Features:
 * 1. Field Parsing:
 *    - Parses <field> nodes, handling optional attributes, labels,
 *      and handles for drag & drop.
 *    - Integrates session-based 'invisible' control for hiding fields dynamically.
 *
 * 2. Widget Parsing:
 *    - Parses <widget> nodes with encoded props for template rendering.
 *    - Assigns unique IDs for widget instances.
 *
 * 3. Button Parsing:
 *    - Parses <button> nodes and groups them into button groups.
 *    - Supports custom attributes such as `striped` and `column_invisible`.
 *    - Handles <header> and <control> nodes for buttons and create actions.
 *
 * 4. GroupBy Parsing:
 *    - Handles <groupby> nodes using a nested GroupListArchParser instance.
 *    - Maintains fieldNodes and button groupings for grouped records.
 *
 * 5. List Attributes:
 *    - Collects metadata for the tree/list view such as editable, multiEdit, limits,
 *      defaultOrder, decorations, openFormView, openAction, and more.
 *    - Integrates active actions including exportXlsx.
 *
 * 6. Integration with Cyllo Studio:
 *    - Stores CyXpath for buttons and fields to enable studio-level DOM manipulation.
 *    - Tracks handle fields for default ordering of list rows.
 *
 * Dependencies:
 * - Odoo core: listView.ArchParser, GroupListArchParser, visitXML, stringToOrderBy
 * - Utility functions: archParseBoolean, getActiveActions, getDecoration, processButton,
 *   encodeObjectForTemplate, combineModifiers
 *
 * Returns:
 * - Object containing parsed columns, fieldNodes, widgetNodes, groupBy info, headerButtons,
 *   creates, and tree/list attributes.
 *
 * Purpose:
 * Enables Cyllo Studio to dynamically edit and render List (Tree) views with custom
 * drag-and-drop, button groups, ribbons, field visibility toggles, and advanced
 * client-side interactivity.
 */
import {listView} from "@web/views/list/list_view";
import {GroupListArchParser} from "@web/views/list/list_arch_parser";
import {visitXML} from "@web/core/utils/xml";
import {stringToOrderBy} from "@web/search/utils/order_by";
import {
    archParseBoolean,
    getActiveActions,
    getDecoration,
    processButton
} from "@web/views/utils";
import {encodeObjectForTemplate} from "@web/views/view_compiler";
import {combineModifiers} from "@web/model/relational_model/utils";

export class CylloListArchParser extends listView.ArchParser {
    parse(xmlDoc, models, modelName) {
        const fieldNodes = {};
        const widgetNodes = {};
        let widgetNextId = 0;
        const columns = [];
        const fields = models[modelName];
        let buttonId = 0;
        const groupBy = {
            buttons: {},
            fields: {},
        };
        let headerButtons = [];
        const creates = [];
        const groupListArchParser = new GroupListArchParser();
        let buttonGroup;
        let handleField = null;
        const treeAttr = {};
        let nextId = 0;
        const fieldNextIds = {};
        visitXML(xmlDoc, (node) => {
            if (node.tagName !== "button") {
                buttonGroup = undefined;
            }
            if (node.tagName === "button") {
                const button = {
                    ...this.processButton(node),
                    defaultRank: "btn-link",
                    type: "button",
                    id: buttonId++,
                    CyXpath: node.getAttribute("cy-xpath"),
                    groups: node.getAttribute("groups") || "",
                };
                if(node.hasAttribute("striped")){
                    button.striped = node.getAttribute("striped")
                }
                if(buttonGroup) {
                    buttonGroup.buttons.push(button);
                    buttonGroup.column_invisible = combineModifiers(
                        buttonGroup.column_invisible,
                        node.getAttribute("column_invisible"),
                        "AND"
                    );
                } else {
                    buttonGroup = {
                        id: `column_${nextId++}`,
                        type: "button_group",
                        buttons: [button],
                        hasLabel: false,
                        column_invisible: node.getAttribute("column_invisible"),
                    };
                    columns.push(buttonGroup);
                }
            } else if(node.tagName === "field") {
                const fieldInfo = this.parseFieldNode(node, models, modelName);
                if (!(fieldInfo.name in fieldNextIds)) {
                    fieldNextIds[fieldInfo.name] = 0;
                }
                const fieldId = `${fieldInfo.name}_${fieldNextIds[fieldInfo.name]++}`;
                fieldNodes[fieldId] = fieldInfo;
                node.setAttribute("field_id", fieldId);
                if (fieldInfo.isHandle) {
                    handleField = fieldInfo.name;
                }
                const label = fieldInfo.field.label;
                const invisible_session = sessionStorage.getItem('invisible');
                const invisible_node = node.getAttribute("optional")
                const optionalAttr = node.getAttribute?.("optional");
                const modifierInvisible = fieldInfo?.modifiers?.invisible || false;
                const attrsInvisible = fieldInfo?.attrs?.invisible || false;
                const isInvisible = optionalAttr === "hide" || modifierInvisible || attrsInvisible;
                columns.push({
                    ...fieldInfo,
                    id: `column_${nextId++}`,
                    className: node.getAttribute("class"), // for oe_edit_only and oe_read_only
                    optional: node.getAttribute("optional") || false,
                    type: "field",
                    striped: isInvisible,
                    hasLabel: !(
                        archParseBoolean(fieldInfo.attrs.nolabel) || fieldInfo.field.noLabel
                    ),
                    label: (fieldInfo.widget && label && label.toString()) || fieldInfo.string,
                });
                return false;
            } else if (node.tagName === "widget") {
                const widgetInfo = this.parseWidgetNode(node);
                const widgetId = `widget_${++widgetNextId}`;
                widgetNodes[widgetId] = widgetInfo;
                node.setAttribute("widget_id", widgetId);

                const widgetProps = {
                    name: widgetInfo.name,
                    // FIXME: this is dumb, we encode it into a weird object so that the widget
                    // can decode it later...
                    node: encodeObjectForTemplate({ attrs: widgetInfo.attrs }).slice(1, -1),
                    className: node.getAttribute("class") || "",
                };
                columns.push({
                    ...widgetInfo,
                    props: widgetProps,
                    id: `column_${nextId++}`,
                    type: "widget",
                });
            } else if (node.tagName === "groupby" && node.getAttribute("name")) {
                const fieldName = node.getAttribute("name");
                const coModelName = fields[fieldName].relation;
                const groupByArchInfo = groupListArchParser.parse(node, models, coModelName);
                groupBy.buttons[fieldName] = groupByArchInfo.buttons;
                groupBy.fields[fieldName] = {
                    fieldNodes: groupByArchInfo.fieldNodes,
                    fields: models[coModelName],
                };
                return false;
            } else if (node.tagName === "header") {
                // AAB: not sure we need to handle invisible="True" button as the usecase seems way
                // less relevant than for fields (so for buttons, relying on the modifiers logic
                // that applies later on could be enough, even if the value is always true)
                headerButtons = [...node.children].map((node) => ({
                    ...this.processButton(node),
                    type: "button",
                    id: buttonId++,
                }));
                return false;
            } else if (node.tagName === "control") {
                for (const childNode of node.children) {
                    if (childNode.tagName === "button") {
                        creates.push({
                            type: "button",
                            ...processButton(childNode),
                        });
                    } else if (childNode.tagName === "create") {
                        creates.push({
                            type: "create",
                            context: childNode.getAttribute("context"),
                            string: childNode.getAttribute("string"),
                        });
                    }
                }
                return false;
            } else if (["tree", "list"].includes(node.tagName)) {
                const activeActions = {
                    ...getActiveActions(xmlDoc),
                    exportXlsx: archParseBoolean(xmlDoc.getAttribute("export_xlsx"), true),
                };
                treeAttr.activeActions = activeActions;

                treeAttr.className = xmlDoc.getAttribute("class") || null;
                treeAttr.editable = xmlDoc.getAttribute("editable");
                treeAttr.multiEdit = activeActions.edit
                    ? archParseBoolean(node.getAttribute("multi_edit") || "")
                    : false;

                treeAttr.openFormView = treeAttr.editable
                    ? archParseBoolean(xmlDoc.getAttribute("open_form_view") || "")
                    : false;

                const limitAttr = node.getAttribute("limit");
                treeAttr.limit = limitAttr && parseInt(limitAttr, 10);

                const countLimitAttr = node.getAttribute("count_limit");
                treeAttr.countLimit = countLimitAttr && parseInt(countLimitAttr, 10);

                const groupsLimitAttr = node.getAttribute("groups_limit");
                treeAttr.groupsLimit = groupsLimitAttr && parseInt(groupsLimitAttr, 10);

                treeAttr.noOpen = archParseBoolean(node.getAttribute("no_open") || "");
                treeAttr.rawExpand = xmlDoc.getAttribute("expand");
                treeAttr.decorations = getDecoration(xmlDoc);

                treeAttr.defaultGroupBy = xmlDoc.getAttribute("default_group_by");
                treeAttr.defaultOrder = stringToOrderBy(
                    xmlDoc.getAttribute("default_order") || null
                );

                // custom open action when clicking on record row
                const action = xmlDoc.getAttribute("action");
                const type = xmlDoc.getAttribute("type");
                treeAttr.openAction = action && type ? { action, type } : null;
            }
        });

        if (!treeAttr.defaultOrder.length && handleField) {
            treeAttr.defaultOrder = stringToOrderBy(handleField);
        }
        return {
            creates,
            headerButtons,
            fieldNodes,
            widgetNodes,
            columns,
            groupBy,
            xmlDoc,
            ...treeAttr,
        };
    }
}