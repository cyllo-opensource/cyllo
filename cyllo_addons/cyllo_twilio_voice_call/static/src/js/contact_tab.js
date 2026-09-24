/** @odoo-module **/
import { useService } from "@web/core/utils/hooks";
import { Component, useState, useRef } from "@odoo/owl";
import { url } from "@web/core/utils/urls";
import { _t } from "@web/core/l10n/translation";
var selectedContact;
var device;

export class ContactTab extends Component {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.contact = useRef("contact")
        this.sid = null,
            this.number = null;
        this.PhoneNumber = null,
            this.state = useState({
                partners: [], // Store fetched partners
                showPartner: false,
                selectedPartner: null,
                wasRejected: false,
                duration: 0,
                number: null,
                call: false
            });
        this.isTimerPaused = false;
        this._fetchPartners();
        this.searchTerms = "";
    }

    /*
       Fetch partners when the component starts
     */
    async _fetchPartners() {
        const partners = await this.orm.searchRead("res.partner", [], ["name", "phone", "image_1920", "mobile"]);
        this.state.partners = partners;
    }

    /*
       To search the contacts
     */
    searchContacts(ev) {
        this.state.searchTerms = (ev.target.value || "").trim().toLowerCase();
    }

    /*
      To get the contacts based on the search results
    */
    get filteredPartners() {
        const searchTerm = this.state.searchTerms;
        if (!searchTerm || !this.state.partners.length) {
            return this.state.partners; // Return all partners if search term is empty or partners list is empty
        }

        return this.state.partners.filter(partner =>
            partner.name.toLowerCase().includes(searchTerm) ||
            (partner.phone && partner.phone.toLowerCase().includes(searchTerm)) // Check if partner has a phone

        )
    }

    /*
       To get the image of the partner
    */
    getImage(partner) {
        return url("/web/image", {
            model: "res.partner",
            id: partner.id,
            field: "avatar_128"
        });
    }

    /*
        To get the contact
    */
    getContact(contact) {
        this.state.showPartner = true
        this.state.selectedPartner = contact
        this.selectedContact = contact
    }

    /*
        To get the image partner
    */
    getImageView(selectedContact) {
        var id = selectedContact.id
        return url("/web/image", {
            model: "res.partner",
            id: parseInt(id),
            field: "avatar_128"
        });
    }

    /*
        To move to the dial pad
    */
    _OnClickNumPad() {
        if (this.props.dial_pad) {
            this.props.dial_pad.state.contacts = false
            this.props.dial_pad.state.value = false
        } else {
            this.props.parent_value.props.dial_pad.state.contacts = false
            this.props.parent_value.props.dial_pad.state.contact = false
        }
    }
    /*
      To minimise and maximizing the templates
    */
    _onClickMinimise() {
        this.props.dial_pad._onClickMinimise()
    }

    /*
       By clicking on it we can move back to the previous screen
    */
    _OnBack() {
        this.state.showPartner = false
    }

    /*
       This functions are used to get the time counter or the duration of the calls,
       when accepting the call even if it is outgoing or incoming.
     */
    _runTimer() {
        if (!this.isTimerPaused) {
            this.timer = setTimeout(() => {
                this.state.duration += 1;
                this._runTimer();
            }, 1000);
        }
    }

    resetTimer() {
        clearTimeout(this.timer);
        this.isTimerPaused = true;
        this.state.duration = 0;
    }

    get timeFormatted() {
        const minutes = Math.floor(this.state.duration / 60);
        const seconds = this.state.duration % 60;
        return `${minutes}:${seconds < 10 ? "0" : ""}${seconds}`;
    }

    /*
        The function is used to check the number is valid or note
    */
    _isValidPhoneNumber(number) {
        // Regex for numbers with a country code
        const phoneRegex = /^\+\d{1,3}\d{4,}$/;
        return phoneRegex.test(number);
    }

    /*
        The function is used to make the outgoing call to the partner we choosing
     */
    async _OnClickCall() {
        device = this.props.dial_pad.device
        var self = this;
        this.number = this.state.selectedPartner.mobile || this.state.selectedPartner.phone;
        var id = this.state.selectedPartner.id
        if (this.number) {
        if (!this._isValidPhoneNumber(this.number)) {
                this.displayNotification(_t("Please check the number before making the call"))
            }
            else{
            var params = {
                To: this.number,
            };
            event.stopPropagation();
            if (device) {
                try {
                    const call = await device.connect({
                        params
                    });
                    this.state.call = true
                    call.on('ringing', (event) => {
                        const callSid = call.parameters.CallSid;
                        this.sid = callSid
                    });
                    /*
                        Wait for the call to have CallSid
                     */
                    call.on('accept', (event) => {
                        const callSid = call.parameters.CallSid;
                        this.sid = callSid; // Store the CallSid for later use
                        this.isTimerPaused = false;
                        this._runTimer();
                        this.orm.call('out.going.call.list', 'action_call', [, this.number, callSid, id]);
                    });

                    call.on('cancel', async (event) => {
                        this.state.call = false;
                        const callSid = call.parameters.CallSid;
                       await this.orm.call('out.going.call.list', 'action_cancel', [, this.number, callSid]);
                        this.action.doAction('soft_reload')
                        this.resetTimer();
                    });

                call.on('disconnect', async (event) => {
                        this.state.call = false;
                        this.resetTimer();
                        this.state.wasRejected = false
                        const callSid = call.parameters.CallSid;
                       if (!this.state.wasRejected) {
                             await this.orm.call('out.going.call.list', 'action_cancel', [, this.number, callSid]).then(() => {
                                this.action.doAction('soft_reload')
                            }).catch((error) => {
                                console.error("Failed to perform soft_reload:", error);
                            });
                        }
                    });

                    call.on('reject', async (event) => {
                        this.state.call = false;
                        const callSid = call.parameters.CallSid;
                      await this.orm.call('out.going.call.list', 'action_cancel', [, this.number, callSid]);
                              this.action.doAction('soft_reload')
                        this.resetTimer();
                    });

                } catch (error) {
                    console.error("Call rejected:", error);
                }
            }
          }
        }
        else{
          this.displayNotification(_t("Please enter a phone number to call"))
        }
    }

    /*
        To create the display notification
    */
    displayNotification(text) {
        this.notification.add(text, {
            type: "warning"
        });
    }

    /*
      The function is used to reject tha call
    */
   async _onClickCancel() {
        var self = this;
        this.state.call = false;
        var PhoneNumber = this.number
        if (!this.sid) {
            this.displayNotification(_t("There is no active call for rejecting."))
        }
        if (device) {
            device.disconnectAll();
            this.state.wasRejected = true
            if (this.state.wasRejected) {
                await this.orm.call('out.going.call.list', 'action_cancel', [, PhoneNumber, this.sid]);
                  this.action.doAction('soft_reload')
            }
        }
        this.resetTimer();
    }
    /*
        By clicking on it we can move to the recent call templates
    */
    _OnRecent() {
        this.props.dial_pad.state.recent = true
        this.props.dial_pad.state.contacts = false
    }
}

ContactTab.template = "contacts_tab";