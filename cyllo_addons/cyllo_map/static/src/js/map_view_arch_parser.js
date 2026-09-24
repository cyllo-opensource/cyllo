/** @odoo-module */

import { visitXML } from "@web/core/utils/xml";
import { stringToOrderBy } from "@web/search/utils/order_by";
import { getActiveActions, archParseBoolean } from "@web/views/utils";
import { Field } from "@web/views/fields/field";
import { Widget } from "@web/views/widgets/widget";

export class MapviewArchParser {
    parse(xmlDoc, models, modelName, ) {
        const fieldNodes = {};
        const widgetNodes = {};
        const fieldNextIds = {};
        const creates = [];
        let handleField = null;
        let headerButtons = [];
        const activeFields = {};
        const columns = [];
        const groupBy = {
            buttons: {},
            fields: {},
        };
        let defaultOrder = stringToOrderBy(xmlDoc.getAttribute("default_order") || null);
        const jsClass = xmlDoc.getAttribute("js_class")
        let startDate = xmlDoc.getAttribute("date_start")
        let endDate = xmlDoc.getAttribute("date_end")
        let Color = xmlDoc.getAttribute("color")
        let defaultGroup = xmlDoc.getAttribute("group_by")
        const activeActions = getActiveActions(xmlDoc);
        activeActions.archiveGroup = archParseBoolean(xmlDoc.getAttribute("archivable"), true);
        activeActions.createGroup = archParseBoolean(xmlDoc.getAttribute("group_create"), true);
        activeActions.deleteGroup = archParseBoolean(xmlDoc.getAttribute("group_delete"), true);
        activeActions.editGroup = archParseBoolean(xmlDoc.getAttribute("group_edit"), true);
        activeActions.quickCreate =
            activeActions.create && archParseBoolean(xmlDoc.getAttribute("quick_create"), true);
        let isLocked = xmlDoc.getAttribute("is_locked")
        visitXML(xmlDoc, (node) => {
            if (node.tagName === "field") {
                const fieldInfo = Field.parseFieldNode(node, models, modelName, "custom_gantt", jsClass);
                if (!(fieldInfo.name in fieldNextIds)) {
                    fieldNextIds[fieldInfo.name] = 0;
                }
                const fieldId = `${fieldInfo.name}_${fieldNextIds[fieldInfo.name]++}`;
                fieldNodes[fieldId] = fieldInfo;
                node.setAttribute("field_id", fieldId);
            } else if (node.tagName === "div" && node.classList.contains("oe_chatter")) {
                return false;
            } else if (node.tagName === "widget") {
                const widgetInfo = Widget.parseWidgetNode(node);
                const widgetId = `widget_${++widgetNextId}`;
                widgetNodes[widgetId] = widgetInfo;
                node.setAttribute("widget_id", widgetId);
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
            defaultOrder,
            activeActions,
            startDate,
            endDate,
            Color,
            defaultGroup,
            isLocked,
            modelName
        };
    }
}
