/** @odoo-module */
import {Component, xml} from "@odoo/owl";
import {SpreadsheetApp} from "../spreadsheet/spreadsheet";
import {registry} from "@web/core/registry";
import {browser} from "@web/core/browser/browser";


export class MainSpreadsheet extends Component {
    static template = xml`<t t-component="spreadsheetComponent" t-props="spreadsheetProps"/>`

    setup() {
        this.resId = false
        this.getResId()
    }

    getResId() {
        this.resId = this.props.action.context?.resId || JSON.parse(browser.sessionStorage.getItem("current_spreadsheet"));
        if (this.resId) {
            browser.sessionStorage.setItem("current_spreadsheet", JSON.stringify(this.resId));
        } else {
            browser.sessionStorage.removeItem("current_spreadsheet");
        }
    }

    get spreadsheetComponent() {
        return SpreadsheetApp
    }

    get spreadsheetProps() {
        return {
            resId: this.resId,
        }
    }
}

registry.category("actions").add("main_spreadsheet", MainSpreadsheet, {force: true});