/** @odoo-module */
import {useComponent, useRef} from "@odoo/owl";
import {useService} from "@web/core/utils/hooks";

export function useSpreadsheet(tref = "fileInput") {
    /*
    * used with template cyllo_spreadsheet.ControlPanel*/
    const ref = useRef(tref)
    const orm = useService("orm")
    const actionService = useService("action");
    const component = useComponent()
    const handleOnChangeUpload = (ev) => {
        const selectedFile = ev.target.files[0];
        const reader = new FileReader();
        try {
            reader.onload = (event) => {
                const arrayBuffer = event.target.result;
                const byteArray = new Uint8Array(arrayBuffer);

                function arrayBufferToBase64(buffer) {
                    let binary = '';
                    const bytes = new Uint8Array(buffer);
                    const len = bytes.byteLength;
                    const chunkSize = 8192;
                    for (let i = 0; i < len; i += chunkSize) {
                        binary += String.fromCharCode.apply(null, bytes.subarray(i, i + chunkSize));
                    }

                    return btoa(binary);
                }

                const base64String = arrayBufferToBase64(byteArray.buffer);

                const name = selectedFile.name;
                if (name.endsWith(".xlsx")) {
                    orm.call("spreadsheet.sheet", 'action_upload_sheet', [], {
                        binary_content: base64String,
                        name,
                    }).then((result) => {
                        component.env.searchModel._notify()
                    }).catch((error) => {
                        console.error('Error uploading file:', error);
                    });
                }
                else {
                    showWarning(`Please upload a .xlsx file`, "danger")
                }
            }
            reader.onerror = (error) => {
                console.error('Error reading file:', error);
            };
            reader.readAsArrayBuffer(selectedFile);
        } catch {
            showWarning(`Please upload a valid document`, "danger")
        }
    }
    const createNew = async () => {
        const [resId,] = await orm.create("spreadsheet.sheet", [{name: "Spreadsheet Unnamed"}]);
        actionService.doAction({
            type: "ir.actions.client",
            tag: "main_spreadsheet",
            context: {
                resId
            }
        })
    }
    const handleUpload = () => {
        ref.el.click()
    }
    const showWarning = (message, type, sticky = false) => {
        actionService.doAction({
            type: 'ir.actions.client',
            tag: 'display_notification',
            params: {
                message,
                type,
                sticky,
            }
        })
    }

    return {
        handleOnChangeUpload,
        handleUpload,
        createNew,
        ref,
    }
}