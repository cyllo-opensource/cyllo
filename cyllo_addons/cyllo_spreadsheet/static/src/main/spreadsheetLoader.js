/** @odoo-module */
import {
    loadSpreadsheetAction
} from "@spreadsheet/assets_backend/spreadsheet_action_loader";
import {registry} from "@web/core/registry";

export async function loadSpreadsheetBundleAction(env, context) {
    await loadSpreadsheetAction(env, "main_spreadsheet", loadSpreadsheetBundleAction)
    env.services.action.doAction({
        type: "ir.actions.client",
        tag: "main_spreadsheet",
        target: "current",
        ...context,
    });
}

registry.category("actions").add("main_spreadsheet", loadSpreadsheetBundleAction);