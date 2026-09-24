/** @odoo-module **/
import { Component } from "@odoo/owl";
import { useState, useRef } from "@odoo/owl";


/* Create new WhatsappPartnerProfile by extending Component */
export class WhatsappPartnerProfile extends Component {
    setup() {
        this.state = useState({countVisible: false,})
        this.root = useRef('profile')
    }

    /*  click of partner triggers a custom event named 'CLICK_PARTNER' using
     the Owl framework's event bus
     */
    clickPartner(ev) {
        this.state.countVisible = true
        this.env.bus.trigger('CLICK_PARTNER', {event: ev, partner: this.props.channel})
        this.env.bus.trigger('UPDATE_COUNTER', {event: ev, partner: this.props.channel})
        var whatsappProfiles = this.__owl__.bdom.parentEl.querySelectorAll('.whatsapp-partner-profile')
        whatsappProfiles.forEach((profile) => {
            profile.classList.remove('active')
        })
        this.root.el.classList.add('active')
    }
}

/* Associate 'WhatsappPartnerProfile' template with the WhatsappPartnerProfile component.*/
WhatsappPartnerProfile.template = 'WhatsappPartnerProfile';