/** @odoo-module */
import { registry } from "@web/core/registry";
import { GanttRenderer } from "./GanttRenderer.js";
import { GanttController } from "./GanttController.js";
import { RelationalModel } from "@web/model/relational_model/relational_model";
import { stringToOrderBy } from "@web/search/utils/order_by";
import { getActiveActions, archParseBoolean } from "@web/views/utils";
import { Field } from "@web/views/fields/field";
import { Widget } from "@web/views/widgets/widget";
import { visitXML } from "@web/core/utils/xml";

class GanttArchParser {
    parse(xmlDoc, relatedModels, modelName, ) {
        const fieldNodes = {};
        const widgetNodes = {};
        const fieldNextIds = {};
        const groupBy = {
            buttons: {},
            fields: {},
        };
        let defaultOrder = stringToOrderBy(xmlDoc.getAttribute("default_order", null));
        let jsClass = xmlDoc.getAttribute("js_class");
        let startDate = xmlDoc.getAttribute("date_start") || xmlDoc.getAttribute("start_date");
        let endDate = xmlDoc.getAttribute("date_stop") || xmlDoc.getAttribute("end_date");
        let color = xmlDoc.getAttribute("color");
        let defaultGroup = xmlDoc.getAttribute("default_group_by") || xmlDoc.getAttribute("group_by");
        const activeActions = getActiveActions(xmlDoc);
        activeActions.archiveGroup = archParseBoolean(xmlDoc.getAttribute("archivable"), true);
        activeActions.createGroup = archParseBoolean(xmlDoc.getAttribute("group_create"), true);
        activeActions.deleteGroup = archParseBoolean(xmlDoc.getAttribute("group_delete"), true);
        activeActions.editGroup = archParseBoolean(xmlDoc.getAttribute("group_edit"), true);
        activeActions.quickCreate = activeActions.create && archParseBoolean(xmlDoc.getAttribute("quick_create"), true);
        let isLocked = xmlDoc.getAttribute("is_locked");
        let showAllData = xmlDoc.getAttribute("show_all");
        visitXML(xmlDoc, (node) => {
            if (node.tagName === "field") {
                const fieldInfo = Field.parseFieldNode(node, relatedModels, modelName, "custom_gantt", jsClass);
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
            fieldNodes,
            widgetNodes,
            groupBy,
            defaultOrder,
            activeActions,
            startDate,
            endDate,
            color,
            defaultGroup,
            isLocked,
            modelName,
            relatedModels,
            showAllData
        };
    }
}
export const GanttView = {
    type: "gantt",
    display_name: "Gantt",
    icon: "ri-menu-unfold-line",
    multiRecord: true,
    Controller: GanttController,
    Renderer: GanttRenderer,
    Model: RelationalModel,
    ArchParser: GanttArchParser,
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
registry.category("views").add("gantt", GanttView);