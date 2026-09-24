/** @odoo-module **/
import {SettingsFormCompiler} from '@web/webclient/settings_form_view/settings_form_compiler'
import {append, createElement} from "@web/core/utils/xml";
import {toStringExpression} from "@web/views/utils";
import {patch} from "@web/core/utils/patch";

const Icons = {
    'stock': 'cyllo_base/static/src/icons/inventory.svg',
    'event': 'cyllo_base/static/src/icons/events.svg',
    'crm': 'cyllo_base/static/src/icons/crm.svg',
    'sale_management': 'cyllo_base/static/src/icons/sales.svg',
    'calendar': 'cyllo_base/static/src/icons/calendar.svg',
    'website': 'cyllo_base/static/src/icons/website.svg',
    'website_slides': 'cyllo_base/static/src/icons/eLearning.svg',
    'purchase': 'cyllo_base/static/src/icons/purchase.svg',
    'mrp': 'cyllo_base/static/src/icons/manufacturing.svg',
    'maintenance': 'cyllo_base/static/src/icons/maintenance.svg',
    'account': 'cyllo_base/static/src/icons/invoicing.svg',
    'project': 'cyllo_base/static/src/icons/project.svg',
    'hr_timesheet': 'cyllo_base/static/src/icons/task-log.svg',
    'mass_mailing': 'cyllo_base/static/src/icons/email-marketing.svg',
    'hr': 'cyllo_base/static/src/icons/employee.svg',
    'hr_recruitment': 'cyllo_base/static/src/icons/recruitment.svg',
    'hr_attendance': 'cyllo_base/static/src/icons/attendance.svg',
    'hr_expense': 'cyllo_base/static/src/icons/expenses.svg',
    'fleet': 'cyllo_base/static/src/icons/fleet.svg',
    'lunch': 'cyllo_base/static/src/icons/lunch.svg',
    'point_of_sale': 'cyllo_base/static/src/icons/pos.svg',
    'general_settings': 'cyllo_base/static/src/icons/cyllo_settings.svg'
} // todo: add icons for cyllo products

patch(SettingsFormCompiler.prototype, {
    setup() {
        super.setup();
    },
    compileApp(el, params) {
        if (el.getAttribute("notApp") === "1") {
            //An app noted with notApp="1" is not rendered.

            //This hack is used when a technical module defines settings, and we don't want to render
            //the settings until the corresponding app is not installed.

            // For example, when installing the module website_sale, the module sale is also installed,
            // but we don't want to render its settings (notApp="1").
            // On the contrary, when sale_management is installed, the module sale is also installed
            // but in this case we want to see its settings (notApp="0").
            return;
        }
        const nameAttr = el.getAttribute("name");
        const path = Icons[nameAttr] || el.getAttribute("logo") || `/${nameAttr}/static/description/icon.png`;
        const module = {
            key: nameAttr,
            string: el.getAttribute("string"),
            imgurl: path
        };
        params.modules.push(module);
        const settingsApp = createElement("SettingsApp", {
            key: toStringExpression(module.key),
            string: toStringExpression(module.string || ""),
            imgurl: toStringExpression(module.imgurl),
            selectedTab: "settings.selectedTab",
            slots: "{}"
        });

        for (const child of el.children) {
            append(settingsApp, this.compileNode(child, params));
        }

        return settingsApp;
    }
})