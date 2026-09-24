/** @odoo-module */
import {
    registry
} from "@web/core/registry";

// Shared filtered content object
const content = (() => {
    const allFields = registry.subRegistries.fields.content;
    const keysToExclude = ["analytic_distribution", "profiling_qweb_view", "property_tags", "gauge", "name_with_subtask_count", "stock_rescheduling_popover", "replenishment_history_widget",
        "lead_days_widget", "code", "iframe_wrapper", "dashboard_graph", "form.email", "form.phone",
        "form.url", "DynamicModelFieldSelectorChar", "domain", "payment", "timepicker", 'popover_widget', "many2many_binary", "pick_from", "project", "base_settings.radio", "statusbar_duration", "forecast_widget", "image_radio", "account_type_selection", "many2many_tags_email", "autosave_many2many_tags", "many2many_tags_avatar_popover", "sml_x2_many", "many2manyattendeeexpandable", "status_with_color", "background_image", "hr_homeworking_radio_image", "char", "reference",
        "char_emojis", "timezone_mismatch"

    ]

    return Object.fromEntries(
        Object.entries(allFields).filter(([key]) => !keysToExclude.includes(key))
    );
})();

/**
 * Exported function to return filtered widget content.
 */
export function widget(params) {
    return{
    defaultWidget: false,
        widgets: content,
    }
}
registry.category("cyllo_studio_widget_list").add("widget_list", widget);
/**
 * Returns a list of widget types from the shared content.
 * @param {string} [selectedType='char'] - Optional fallback type.
 */
export function getWidgetTypes(selectedType = 'char') {
    const widgetTypes = [];

    Object.entries(content).forEach(
        ([key, value]) => {
            if (key.includes(".") && key.split(".")[0] == 'kanban') {
                return;
            }
            if (value[1].supportedTypes && value[1].supportedTypes.includes(selectedType)) {
                const widget = {
                    value: key,
                    label: `${value[1].displayName || ""} (${key.split(".").pop()})`,
                };
                if (value[1].extractProps || value[1].component.name == 'HandleField') {
                    widgetTypes.push(widget)
                }
            }
        })
    return widgetTypes;
}

export function getWidgetSupport(widget_name) {
    if (!content || !widget_name) return [];

    let supportedOptions = content[widget_name]?.[1]?.supportedOptions || '';

    if (widget_name === 'monetary' && Array.isArray(supportedOptions)) {
        supportedOptions = supportedOptions.filter(item => item.name !== "no_symbol");
    }

    if (supportedOptions && typeof supportedOptions === 'object') {
        return Object.entries(supportedOptions).map(([key, option]) => ({
            id: key,
            label: option.name,
            options: {
                ...option
            }
        }));
    }

    return [];
}