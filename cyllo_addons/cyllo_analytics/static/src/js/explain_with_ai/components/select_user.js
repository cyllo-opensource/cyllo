/** @odoo-module **/
const { useState, Component, useRef, onWillStart, onMounted, useEffect } = owl;
import { Dialog } from "@web/core/dialog/dialog";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";
import { useService } from "@web/core/utils/hooks";
import { MultiRecordSelector } from "@web/core/record_selectors/multi_record_selector";

export class SelectUser extends Component {
    setup() {
        this.notification = useService("notification")
        this.orm = useService('orm')
        this.state = useState({ currentValue: []})
    }
    getDomain() {
        const ids = this.state.currentValue.map(item => item[0])
        let domain = ids.length ? [["id","not in", ids]] : []
        return domain
    }
    deleteRecord(value) {
        this.state.currentValue = this.state.currentValue.filter(item => item[0] !== value[0])
    }
    async onSelect(ev) {
        var newValue = await this._nameGet(ev[0].id);
        const { currentValue } = this.state;
        const recordId = newValue[0];
        const exists = currentValue.find((rec) => rec[0] === recordId);
        this.getDomain()
        if (exists) {
            return;
        }
        this.state.currentValue = [...currentValue, newValue];
    }
    async _nameGet(recordId) {
        const result = await this.orm.read("res.users", [recordId], ["display_name"], {
            context: this.props.context,
        });
        return [result[0].id, result[0].display_name];
    }
    sendChart(ev){
        if (this.state.currentValue.length > 0){
            this.props.handleSendToUser({ currentValue: this.state.currentValue })
            this.notification.add("Message has been sent successfully",{type: "success"})
            this.props.close();
        }
        else{
            this.notification.add("Please add a user",{type: "warning"})
        }
    }
}

SelectUser.template = "SelectUser";
SelectUser.components = {
    Dialog, Many2XAutocomplete,MultiRecordSelector
}