/* @odoo-module */

import {Component, useState} from "@odoo/owl";
import {Dialog} from "@web/core/dialog/dialog";
import {useService} from "@web/core/utils/hooks";

export class Authentication extends Component {
    static template = "authentication"
    static components = {Dialog}

    setup() {
        this.state = useState({
            password: "",
            isCheckedOnce: false,
        })
        this.orm = useService('orm')
        this.action = useService('action')
    }

    handleAuthClose() {
        this.props.close()
    }
    async handleKeyDown(ev) {
        if (ev.key === "Enter") {
            await this.handleAuthConfirm()
        }
    }

    get passwordClass() {
        return this.state.isCheckedOnce ? this.state.password.length ? '' : 'wrong-password' : ''
    }

    async handleAuthConfirm() {
        const {resId, resModel, method, data} = this.props
        const response = await this.orm.call(resModel, method, [resId, this.state.password])
        if (response) {
            await this.props.confirm(data)
            this.handleAuthClose()
        } else {
            this.action.doAction({
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': "Incorrect Password",
                    'type': 'danger',
                    'sticky': false,
                }
            })
            this.state.isCheckedOnce = true
            this.state.password = ''
        }
    }
}