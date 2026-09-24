/** @odoo-module **/
import { useService } from "@web/core/utils/hooks";
import { Component, useState, useRef, onMounted, onWillUnmount, onWillUpdateProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { jsonrpc } from "@web/core/network/rpc_service";
import { RecentTab } from '@cyllo_twilio_voice_call/js/recent_tab'
import { ContactTab } from '@cyllo_twilio_voice_call/js/contact_tab'
var device;

export class DialPad extends Component {
    static template = "dial_pad";
    setup() {
        super.setup(...arguments);
        this.action = useService("action");
        this.keys = useRef("keys");
        this.clearAll = useRef("clear-all");
        this.clearDelete = useRef("clear-delete");
        this.outgoing = useRef("keypad")
        this.notification = useService("notification");
        this.countrySelect = useRef("countrySelect");
        this.sid = null;
        this.number = null;
        this.PhoneNumber = null,
            this.callAction = null,
            this.timer = null,
            this.orm = useService("orm");
        onMounted(() => {
            this.fetch_data();
            if (this.props?.number) {
                this.callFormNumber(this.props?.number)
            }
        });
        onWillUpdateProps((nextProps) => {

            if (nextProps?.number) {
                this.callFormNumber(nextProps?.number)
            }


        });

        this.state = useState({
            value: false,
            selectedCountryCode: '+91',
            selectedPartner: null,
            duration: 0,
            wasRejected: false,
            recent: false,
            contacts: false,
            isPartner: false,
            isRejected: false,
            cancel: false,
            number: null,
            countryCode: '+1'
        })
        this.isTimerPaused = false;
    }
    /* The function 'fetch_data' for initializing the device,
       and creating the access token for making and receiving the calls
     */
    fetch_data() {
        var self = this;
        // Call the server to get a new token
        return jsonrpc('/access/token', {})
            .then(function (response) {
                if (response && response.status === "configured" && response.token) {
                    device = new Twilio.Device(response.token, {
                        codecPreferences: ["opus", "pcmu"],
                        fakeLocalDTMF: true,
                        enableRingingState: true,
                    });
                    self.device = device;
                    device.register();
                }
            })
            .catch(function (error) {
                self.displayNotification(_t("Error fetching Twilio token."), 'danger');
            });
    }
    /* The function 'callFormNumber' is used to add the number into twilio dialpad
    */
    callFormNumber(fullNumber) {
        var minimiseIcon = this.outgoing.el.querySelector('.minimise');
        if (!minimiseIcon) {
            this._onClickMinimise()
        }
        const number = fullNumber?.trim() || "";
        setTimeout(() => {
            const countrySelect = this.countrySelect.el;

            const countryOptions = Array.from(countrySelect.options).map(o => o.value);

            if (!number.startsWith("+")) {
                this.state.countryCode = '+1'
                this.state.number = number;
                return;
            }
            const countryMatch = countryOptions.find(code => number.startsWith(code));

            if (countryMatch) {

                this.state.countryCode = countryMatch;
                this.state.number = number.slice(countryMatch.length);
            } else {
                this.state.countryCode = '+1'
                this.state.number = number;
            }
        }, 0);
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
       The function is used to clear the numbers in the screen
    */
    _onClickScreen(event) {
        const clickedButton = event.target;
        if (clickedButton.classList.contains('cy-dialing-nmbr')) {
            const buttonText = clickedButton.textContent;
            this.keys.el.value += buttonText;
        }
    }

    /* To Clear the numbers */
    _OnClear() {
        this.keys.el.value = this.keys.el.value.slice(0, -1);
    }
    _OnClearAll(){
        this.keys.el.value = ''
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
        The function is used to check the number is valid or note
    */
    _isValidPhoneNumber(number) {
        // Regex for numbers with a country code
        const phoneRegex = /^\+\d{1,3}\d{4,}$/;
        return phoneRegex.test(number);
    }

    updatePhoneNumber(event) {
        this.state.countryCode = event.target.value;
    }

    /*
        For making outgoing calls
    */
    async _onClickCall() {
        var self = this;
        const callButton = this.outgoing.el.querySelector('.cy-call-btn');
        const callClear = this.outgoing.el.querySelector('.cy-dial_clearbtn');
        this.PhoneNumber = this.state.countryCode + this.keys.el.value;
        try {
            const PartnerId = await this.orm.searchRead("res.partner", [
                "|",
                ["phone", "=", this.PhoneNumber],
                ["mobile", "=", this.PhoneNumber]
            ], ['image_1920', 'name']);

            if (PartnerId && PartnerId.length > 0) {
                this.state.selectedPartner = PartnerId;
                this.state.isPartner = true;
                this.state.selectedPartner.image_1920 = PartnerId[0].image_1920;
                this.state.selectedPartner.partner_name = PartnerId[0].name;
            }
            var id = (PartnerId && PartnerId.length > 0) ? PartnerId[0].id : null;
            if (this.PhoneNumber) {
                if (!this._isValidPhoneNumber(this.PhoneNumber)) {
                    this.displayNotification(_t("Please enter the correct phone number with the country code"), 'danger');
                } else {
                    var params = { To: this.PhoneNumber };
                    event.stopPropagation();
                    if (self.device) {
                        try {
                            // Listening to the error event on the device object
                            self.device.on('error', (error) => {
                                this.displayNotification(_t("Cannot connect due to incorrect credentials, please test your connection in the settings"), 'danger');
                            });
                            const call = await self.device.connect({ params });
                            this.callAction = call;
                            this.state.value = true;
                            this.state.cancel = true;
                            callButton.style.display = 'none';
                            callClear.style.display = 'none';
                            call.on('ringing', (event) => {
                                const callSid = call.parameters.CallSid;
                                this.sid = callSid;
                            });
                            call.on('accept', (event) => {
                                const callSid = call.parameters.CallSid;
                                this.sid = callSid;
                                this.isTimerPaused = false;
                                this._runTimer();
                                if (id) {
                                    this.orm.call('out.going.call.list', 'action_call', [, this.PhoneNumber, callSid, id]);
                                } else {
                                    this.orm.call('out.going.call.list', 'action_making_call', [, this.PhoneNumber, callSid]);
                                }
                            });
                            call.on('cancel', async (event) => {
                                this.state.value = false;
                                this.state.cancel = false;
                                callButton.style.display = 'block';
                                callClear.style.display = 'block';
                                const callSid = call.parameters.CallSid;
                                await this.orm.call('out.going.call.list', 'action_cancel', [, this.PhoneNumber, callSid]);
                                this.action.doAction('soft_reload');
                                this.resetTimer();
                            });

                            call.on('disconnect', async (event) => {
                                this.state.value = false;
                                this.state.cancel = false;
                                callButton.style.display = 'block';
                                callClear.style.display = 'block';
                                this.resetTimer();
                                const callSid = call.parameters.CallSid;

                                if (!this.state.wasRejected && !this.state.isRejected) {
                                    try {
                                        await this.orm.call('out.going.call.list', 'action_cancel', [, this.PhoneNumber, callSid]);
                                        this.action.doAction('soft_reload');
                                    } catch (error) {
                                        console.error("Failed to perform action_cancel:", error);
                                    }
                                }
                            });

                            call.on('reject', async (event) => {
                                this.state.value = false;
                                this.state.cancel = false;
                                const callSid = call.parameters.CallSid;

                                await this.orm.call('out.going.call.list', 'action_cancel', [, this.PhoneNumber, callSid]);
                                this.action.doAction('soft_reload');
                                this.resetTimer();
                                callButton.style.display = 'block';
                                callClear.style.display = 'block';
                            });

                        } catch (error) {
                            this.displayNotification(_t("Connection Error. Please try again."), 'danger');
                            callButton.style.display = 'block';
                            callClear.style.display = 'block';
                        }
                    } else {
                        this.displayNotification(_t("Twilio Configuration is incomplete, Please set the Account SID, Auth Token, and the Phone Number"), 'danger');
                    }
                }
            } else {
                this.displayNotification(_t("Please enter a phone number to call"), 'danger');
            }
        } catch (generalError) {
            this.displayNotification(_t("An unexpected error occurred. Please try again."), 'danger');
            callButton.style.display = 'block';
            callClear.style.display = 'block';
        }

}
    /*
        For rejecting or disconnecting the active call
    */
  async _onClickCancel() {
        var self = this;
        this.state.value = false;
        this.state.cancel = false;
        this.state.isRejected = true;
        var PhoneNumber = this.PhoneNumber
        if (!this.sid) {
            this.displayNotification(_t("There is no active call for rejecting."))
        }
        if (self.device) {
            self.device.disconnectAll();
            this.state.wasRejected = true
            if (this.state.wasRejected) {
                await this.orm.call('out.going.call.list', 'action_cancel', [, PhoneNumber, this.sid]);
                this.action.doAction('soft_reload')
            }
        }
        this.resetTimer();
    }
    /*
       To minimize and maximise the templates
    */
    _onClickMinimise() {
        var outgoingDiv = this.outgoing.el.querySelector('.outgoing');
        var closeBtn = this.outgoing.el.querySelector('.close-btn');
        var outgoingKeypad = this.outgoing.el;
        var minimiseIcon = this.outgoing.el.querySelector('.minimise');
        var icon = this.outgoing.el.querySelector('.mini');
        if (outgoingDiv.style.display === 'none') {
            outgoingDiv.style.display = 'block';
            closeBtn.style.display = 'flex';
            outgoingKeypad.style.width = '19%';
            outgoingKeypad.style.minWidth = '340px';
            outgoingKeypad.style.borderRadius = '0px';
            outgoingKeypad.style.removeProperty('height');
            outgoingKeypad.style.backgroundColor = '#fff';
            if (!minimiseIcon) {
                icon.classList.remove('ri-phone-fill');
                icon.classList.add('ri-subtract-fill');
                icon.style.fontSize = ''
                icon.style.marginRight = ''
                icon.style.marginBottom = ''
                icon.style.color = 'black';
                icon.classList.add('minimise');
            }
        } else {
            outgoingDiv.style.display = 'none';
            closeBtn.style.display = 'none';
            outgoingKeypad.style.width = '64px';
            outgoingKeypad.style.minWidth = '0';
            outgoingKeypad.style.bottom = '20px !important';
            outgoingDiv.style.bottom = '20px !important';
            outgoingKeypad.style.height = '64px';
            outgoingKeypad.style.borderRadius = '50%';
            outgoingKeypad.style.backgroundColor = '';
            if (minimiseIcon) {
                minimiseIcon.classList.add('ri-phone-fill');
                minimiseIcon.classList.remove('ri-subtract-fill');
                minimiseIcon.classList.remove('minimise');
                outgoingKeypad.style.backgroundColor = '#9EA700';
                minimiseIcon.style.color = 'white';
                minimiseIcon.style.fontSize = '30px'
            }
        }
    }
    /*
      By clicking on it we can move to the recent tab
    */
    _onClickRecent() {
        this.state.recent = true
        this.state.value = true
    }
    /*
      By clicking on it we can move to the contact tab
    */
    _onClickContact() {
        this.state.contacts = true
        this.state.value = true
    }
}

DialPad.components = {
    RecentTab,
    ContactTab
}
