/** @odoo-module */
import {registry} from "@web/core/registry";
import {UserShare} from "../views/userShare/userShare";
import {download} from "@web/core/network/download";


const loadShareToUser = (env, action) => {
    env.services.dialog.add(UserShare, {
        selected: action.context.active_ids
    })
}
registry.category("actions").add("share_to_user_spreadsheet", loadShareToUser);


const downloadSpreadsheet = (env, action) => {
    const {files, name} = action.params
    download({
        url: "/spreadsheet/download/documents",
        data: {
            files,
            name,
        },
    })

}
registry.category("actions").add("download_spreadsheet", downloadSpreadsheet);