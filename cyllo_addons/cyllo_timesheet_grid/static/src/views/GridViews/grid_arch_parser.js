/** @odoo-module **/
import { visitXML } from "@web/core/utils/xml";
import { Field } from "@web/views/fields/field";
import { addFieldDependencies, archParseBoolean, processButton } from "@web/views/utils"
import { Widget } from "@web/views/widgets/widget";
const SCALES = ["day", "week", "month", "year"];
export class GroupListArchParser {
    parse(arch, models, modelName, jsClass) {
        const fieldNodes = {};
        const fieldNextIds = {};
        const buttons = [];
        let buttonId = 0;
        visitXML(arch, (node) => {
            if (node.tagName === "button") {
                buttons.push({
                    ...processButton(node),
                    id: buttonId++,
                });
                return false;
            } else if (node.tagName === "field") {
                const fieldInfo = Field.parseFieldNode(node, models, modelName, "list", jsClass);
                if (!(fieldInfo.name in fieldNextIds)) {
                    fieldNextIds[fieldInfo.name] = 0;
                }
                const fieldId = `${fieldInfo.name}_${fieldNextIds[fieldInfo.name]++}`;
                fieldNodes[fieldId] = fieldInfo;
                node.setAttribute("field_id", fieldId);
                return false;
            }
        });
        return { fieldNodes, buttons };
    }
}
export class GridArchParser{
    /**
     * Check if a column is visible based on the column invisible modifier.
     * @param {boolean} columnInvisibleModifier - The column invisible modifier.
     * @returns {boolean} - True if the column is visible, false otherwise.
     */
    isColumnVisible(columnInvisibleModifier) {
        return columnInvisibleModifier !== true;
    }
    /**
     * Parse a field node and return the parsed field information.
     * @param {Node} node - The field node to parse.
     * @param {Object} models - The models information.
     * @param {string} modelName - The name of the model.
     * @returns {Object} - The parsed field information.
     */
    parseFieldNode(node, models, modelName) {
        return Field.parseFieldNode(node, models, modelName, "grid");
    }

    parseWidgetNode(node, models, modelName) {
        return Widget.parseWidgetNode(node);
    }

    processButton(node) {
        return processButton(node);
    }
    /**
     * Parse the grid view architecture.
     * @param {string} arch - The XML architecture to parse.
     * @param {Object} models - The models information.
     * @param {string} modelName - The name of the model.
     * @returns {Object} - The parsed grid view architecture.
     */
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
        const treeAttr = {
            limit: 200,
        };
        let nextId = 0;
        const activeFields = {};
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
                };
                if (buttonGroup) {
                    buttonGroup.buttons.push(button);
                    buttonGroup.column_invisible = combineModifiers(buttonGroup.column_invisible, node.getAttribute('column_invisible'), "AND");
                } else {
                    buttonGroup = {
                        id: `column_${nextId++}`,
                        type: "button_group",
                        buttons: [button],
                        hasLabel: false,
                        column_invisible: node.getAttribute('column_invisible'),
                    };
                    columns.push(buttonGroup);
                }
            } else if (node.tagName === "field") {
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
                columns.push({
                    ...fieldInfo,
                    id: `column_${nextId++}`,
                    className: node.getAttribute("class"), // for oe_edit_only and oe_read_only
                    optional: node.getAttribute("optional") || false,
                    type: "field",
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
                addFieldDependencies(widgetInfo, activeFields, models[modelName]);

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
                const xmlSerializer = new XMLSerializer();
                const groupByArch = xmlSerializer.serializeToString(node);
                const coModelName = fields[fieldName].relation;
                const groupByArchInfo = groupListArchParser.parse(groupByArch, models, coModelName);
                groupBy.buttons[fieldName] = groupByArchInfo.buttons;
                groupBy.fields[fieldName] = {
                    activeFields: groupByArchInfo.activeFields,
                    fieldNodes: groupByArchInfo.fieldNodes,
                    fields: models[coModelName],
                };
                return false;
            } else if (node.tagName === "header") {
                // AAB: not sure we need to handle invisible="1" button as the usecase seems way
                // less relevant than for fields (so for buttons, relying on the modifiers logic
                // that applies later on could be enough, even if the value is always true)
                headerButtons = [...node.children]
                    .map((node) => ({
                        ...processButton(node),
                        type: "button",
                        id: buttonId++,
                    }))
                    .filter((button) => button.modifiers.invisible !== true);
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
            }
        });
        return {
            creates,
            handleField,
            headerButtons,
            fieldNodes,
            widgetNodes,
            activeFields,
            columns,
            groupBy,
            xmlDoc,
            ...treeAttr,
        };
    }
}