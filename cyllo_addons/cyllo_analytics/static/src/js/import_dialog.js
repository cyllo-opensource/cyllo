/** @odoo-module **/
import { Component, useRef} from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";

export class ImportDialog extends Component {
    /**
     *handle the json file and import the data
     **/
    setup() {
        this.orm = useService("orm")
        this.actionService = useService("action")
        this.root = useRef("root")
        this.notification = useService("notification")
        this.file = false
    }
    onChangeFileInput(ev) {
        this.file = false
        const { files } = ev.target
        if (!files[0]) return;
        if (this.isValidFormat(files[0])){
            this.file = files[0]
        }
        else {
            this.showMessage('Error reading the file: Not a valid JSON file', 'danger')
        }
    }
    async onFileUpload(ev) {
        if (this.file){
            var reader = new FileReader();
            reader.readAsText(this.file);
            reader.onload = async (e) => {
                try {
                    this.data = JSON.parse(reader.result);
                    const [response, error] = await this.orm.call("dashboard.config", "import_data", [this.data]);
                    var message = response ? 'Successfully Imported' : `An error occurred during data import: Warning '${error}'`
                    var type = response ? 'success' : 'danger'
                    this.props.close();
                    this.showMessage(message, type)
                    this.actionService.doAction("soft_reload")
                }
                catch {
                    return this.showMessage('Error reading the file: Not a valid JSON file', 'danger')
                }
            }
        }
        else {
            this.root.el.classList.add("alert_input_class")
        }
    }
    onFocus() {
        this.root.el.classList.remove("alert_input_class")
    }
    showMessage(message, type) {
        this.notification.add(message, {
            type
        })
    }
    isValidFormat(data) {
        return (data.type === "application/json");
    }
    cancel() {
        this.props.close();
    }
}

ImportDialog.template = "cyllo_analytics.ImportDialog"
ImportDialog.components = { Dialog }