/** @odoo-module **/
import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

/* Create new WhatsappWelcome by extending Component */
export class ChatOption extends Component {
    setup() {
        this.actionService = useService("action");
        this.orm = useService('orm')
    }

    async createLead() {
        let channel = await this.orm.read("whatsapp.channel", [this.props.message.channel_id[0]], []);
        let leadValues = {
            'name': channel[0].partner_id[1] + " 's" + " opportunity",
            'description': this.props.message.message,
            'partner_id': channel[0].partner_id[0]
        }
        let lead = await this.orm.create("crm.lead", [leadValues], []);
        if (this.props.message.attachment_id[0]) {
            let messageValues = {
                'model': 'crm.lead',
                'res_id': lead[0],
                'attachment_ids': [this.props.message.attachment_id[0]]
            }
            await this.orm.create("mail.message", [messageValues], []);
        }
        await this.actionService.doAction({
            res_model: "crm.lead",
            res_id: lead[0],
            views: [[false, "form"]],
            type: "ir.actions.act_window",
            view_mode: "form",
            target: "new",
        });
    }
}

/* Associate 'WhatsappWelcome' template with the WhatsappWelcome component.*/
ChatOption.template = 'ChatOption';