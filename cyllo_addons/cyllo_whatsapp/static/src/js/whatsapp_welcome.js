/** @odoo-module **/
import {Component, useState} from "@odoo/owl";
import {useService} from "@web/core/utils/hooks";

/* Create new WhatsappWelcome by extending Component */
export class WhatsappWelcome extends Component {
    setup() {
        this.orm = useService('orm')
        this.checkWhatsappConfiguration()
        this.state = useState({
            checkWhatsappConfiguration : true
        })

    }

    async checkWhatsappConfiguration() {
        let result = await this.orm.call(
            "res.users",
            'get_whatsapp_configuration'
        )
        this.state.checkWhatsappConfiguration = result
    }

    onClickConfiguration(){
        this.env.bus.trigger('on_Click_Configuration')
    }
}

/* Associate 'WhatsappWelcome' template with the WhatsappWelcome component.*/
WhatsappWelcome.template = 'WhatsappWelcome';