/* @odoo-module */
import { patch } from "@web/core/utils/patch";
import { PhoneField }  from "@web/views/fields/phone/phone_field"
import { useService } from "@web/core/utils/hooks";
import { CallOptionModal } from "@cyllo_twilio_voice_call/js/call_option_modal";

patch(PhoneField.prototype,{

    setup() {
     super.setup();
     this.dialog = useService("dialog");
    },

    callOption(ev) {
        ev.preventDefault();
        const phoneNumber = this.props.record.data[this.props.name];
        this.dialog.add(CallOptionModal, {
            phoneNumber,
            onSelect: (option) => this.handleOption(option, phoneNumber),
        });
    },

    handleOption(option, phoneNumber) {
        if (option === "twilio") {
            this.env.bus.trigger('CALL_ACTION',{number:phoneNumber})
        } else if (option === "regular") {
            window.open(`tel:${phoneNumber}`, "_self");
        } else {
            console.error("Unknown option:", option);
        }
    }

})
