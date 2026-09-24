/** @odoo-module */
import {Component, onWillStart, status, useRef, useState, useSubEnv} from "@odoo/owl";
import {useService} from "@web/core/utils/hooks";
import * as spreadsheet from "@odoo/o-spreadsheet";
import {migrate} from "@spreadsheet/o_spreadsheet/migration";
import {_t} from "@web/core/l10n/translation";
import {useSetupAction} from "@web/webclient/actions/action_hook";
import {download} from "@web/core/network/download";
import {UserShare} from "../views/userShare/userShare";
import {addShareToMenu} from "../topMenuRegistry/topMenuRegistry";

const {Spreadsheet, Model} = spreadsheet;

export class SpreadsheetApp extends Component {
    static template = "Spreadsheet"
    static components = {Spreadsheet}

    setup() {
        this.orm = useService("orm")
        this.effect = useService("effect")
        this.dialog = useService("dialog")
        this.resId = this.props.resId;
        this.root = useRef('root')
        onWillStart(this.loadData)
        this.state = useState({
            data: {},
            hasData: false,
            accessData: {is_admin: false, access: false}
        })
        useSetupAction({
            beforeLeave: this.handleBeforeUnload.bind(this),
            beforeUnload: this.handleBeforeUnload.bind(this)
        })
        useSubEnv({
            saveSheet: this.saveSheet.bind(this),
            raiseError: this.raiseError.bind(this),
            notifyUser: this.notifyUser.bind(this),
            download: this.download.bind(this),
            share: this.share.bind(this),
            updateName: this.updateName.bind(this),
        });
        this.spreadsheetData = false
        this.shareAdded = false
    }

    async updateName(name) {
        if (!name.endsWith('.xlsx')) {
            name += ".xlsx"
        }
        await this.orm.write("spreadsheet.sheet", [this.resId], {
            name
        })
    }

    share() {
        this.dialog.add(UserShare, {selected: [this.resId]})
    }

    async snapshot() {
        if (status(this) !== "destroyed" && this.root.el) {
            const element = this.root.el.querySelector(".o-grid-container");
            const canvas = await html2canvas(element);
            return canvas.toDataURL('image/png').split(',')[1]; // Return the captured data
        } else {
            console.warn("Couldn't capture the template");
            return false;
        }
    }


    get hasData() {
        return this.state.hasData
    }

    notifyMessage({title, message, notifType}) {
        this.effect.add({
            title: title || _t("Warning"),
            message: message || "",
            type: "notification_panel",
            notificationType: notifType || "warning",
        })
    }

    notifyUser(notification) {
        this.notifyMessage({message: notification.text})
    }

    raiseError(message) {
        this.notifyMessage({message})
    }

    async loadData() {
        if (this.resId) {
            const [data, accessData] = await this.orm.call("spreadsheet.sheet", "get_spreadsheet_data", [this.resId]);
            this.state.data = data
            this.state.accessData = accessData
            this.processSpreadsheet()
        }
    }

    get recordMode() {
        const {access} = this.state.accessData
        return access ? access === 'write' ? 'normal' : 'readonly' : 'readonly'
    }

    processSpreadsheet() {
        if (this.state.accessData.is_admin && !this.shareAdded) {
            addShareToMenu()
            this.shareAdded = true
        }
        this.spreadsheetData = new Model(
            migrate(this.state.data.sheet_json), {
                mode: this.recordMode,
                name: this.state.data.name
            }
        ); //TODO: Live Editing with multiple users
        this.state.hasData = true;
    }

    async handleBeforeUnload() {
        await this.saveSheet()
    }

    async saveSheet() {
        const data = this.spreadsheetData.exportData()
        await this.updateSheet(data)
    }

    async download() {
        const {files} = this.spreadsheetData.exportXLSX();
        let name = this.spreadsheetData.config.name
        if(name == ".xlsx" || name == "Spreadsheet Unnamed")
        {
            name = "Spreadsheet"
        }
        download({
            url: "/spreadsheet/download",
            data: {
                files: JSON.stringify(files),
                name,
            },
        })
    }

    async updateSheet(sheet_json) {
        if (this.recordMode !== 'readonly') {
            const image_1920 = await this.snapshot()
            status(this) !== "destroyed" && this.resId && await this.orm.call("spreadsheet.sheet", "update_sheet", [this.resId], {
                sheet_json, image_1920
            })
        }
    }
}