/** @odoo-module **/
import { useService } from "@web/core/utils/hooks";
import { Component, useState, useRef } from "@odoo/owl";
import { ContactTab } from '@cyllo_twilio_voice_call/js/contact_tab'
import { _t } from "@web/core/l10n/translation";
var device;

export class RecentTab extends Component {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.recentTab = useRef("recent")
        this.action = useService("action");
        this.notification = useService("notification");
        this.sid = null, // Initialize callSid as null
        this.number = null,
        this.state = useState({
            recent: [], // Store fetched partners
            showPartner: false,
            recent_out: [],
            mergedRecent: [],
            mergedData: [],
            contact: false,
            selectedPartner: null,
            call: false,
            wasRejected: false,
            duration: 0,
            number: null,
        });
        this.isTimerPaused = false;
        this._fetchRecentCall();
        this._fetchRecentCallOut();
        this.searchTerms = "";
        this.mergeAndSortData()
    }

    /*
    Fetch incoming call list
    */
    async _fetchRecentCall() {
        try {
            const recent = await this.orm.searchRead("incoming.call.list",[],["from_number", "start_time", "duration", "image_1920", "partner_id"],
            { order: 'start_time DESC' }); // Fetch incoming calls with specific fields sorted by start_time in descending order
            this.state.recent = recent;
        } catch (error) {
            console.error("Error fetching incoming calls:", error);
        }
        this.mergeAndSortData();
    }

    /*
    Fetch outgoing call list
    */
    async _fetchRecentCallOut() {
        try {
            const recent_out = await this.orm.searchRead("out.going.call.list",[],["to_number", "start_time", "duration", "image_1920", "partner_id"],
                { order: 'start_time DESC' });// Fetch partners with specific fields sorted by start_time in descending order
            this.state.recent_out = recent_out;
        } catch (error) {
            console.error("Error fetching partners:", error);
        }
        this.mergeAndSortData();
    }

    /*
      To merge incoming and outgoing calls
    */
    mergeAndSortData() {
        try {
            var combined_data = this.state.recent.concat(this.state.recent_out);
            var sorted_data = combined_data.sort((a, b) => new Date(b.start_time) - new Date(a.start_time));
            // Add current user's time to the start_date field in merged data
            const mergedDataWithUserTime = sorted_data.map((item,index) => {
                // Get start_date from the item in this.state.recent
                var startDate = new Date(item.start_time);
                // Get the current user's time based on the start_date's timezone
                var userTimeZoneOffset = startDate.getTimezoneOffset();
                var userDateTime = new Date(startDate.getTime() - userTimeZoneOffset * 60 * 1000);
                // Format the date to the desired format
                var userDate = ('0' + userDateTime.getDate()).slice(-2) + '/' + ('0' + (userDateTime.getMonth() + 1)).slice(-2) + '/' + userDateTime.getFullYear();
                var userTime = ('0' + userDateTime.getHours()).slice(-2) + ':' + ('0' + userDateTime.getMinutes()).slice(-2) + ':' + ('0' + userDateTime.getSeconds()).slice(-2);
                var userDateTimeFormatted = userDate + ' ' + userTime;
                return {
                    ...item,
                    start_time: userDateTimeFormatted, // Update start_time to current user's time for each item
                    serial: index + 1 // Add a serial number based on the index of the item in the merged array
                };
            });
            this.state.mergedRecent = mergedDataWithUserTime;
        } catch (error) {
            console.error("Error merging and sorting data:", error);
        }
    }

    /*
    To search contacts
    */
    searchRecent(ev) {
        this.state.searchTerms = (ev.target.value || "").trim().toLowerCase();
    }

    /*To get partners based on the search results*/
    get filteredPartners() {
        const searchTerm = this.state.searchTerms;
        if (!searchTerm || !this.state.mergedRecent.length) {
            return this.state.mergedRecent; // Return all partners if search term is empty or partners list is empty
        }
        return this.state.mergedRecent.filter(recent =>
            (recent.from_number && recent.from_number.includes(searchTerm)) || // Check from_number
            ((recent.partner_id && recent.partner_id[1]) && recent.partner_id[1].toLowerCase().includes(searchTerm)) || // Check partner_id and its name
            (recent.to_number && recent.to_number.includes(searchTerm)) // Check to_number
        );
    }

    /*To move to the dial pad*/
    _OnClickNumPad() {
        this.props.dial_pad.state.recent = false
        this.props.dial_pad.state.value = false
    }

    /*To move to the previous page*/
    _OnBack() {
        this.state.showPartner = false
    }

    /*
    Minimizing maximizing of the templates.
    */
    _onClickMinimise() {
        var RecentDiv = this.recentTab.el.querySelector('.recent-tab');
        var closeBtn = this.recentTab.el.querySelector('.close-btn');
        var RecentTab = this.recentTab.el;
        var minimiseIcon = this.recentTab.el.querySelector('.minimise');
        var icon = this.recentTab.el.querySelector('.mini');

        if (RecentDiv.style.display === 'none') {
            RecentDiv.style.display = 'block';
            closeBtn.style.display = 'flex';
            RecentTab.style.minWidth = '342px';
            RecentTab.style.borderRadius = '0px';
            RecentTab.style.removeProperty('height');
            RecentTab.style.backgroundColor = 'white';
            if (!minimiseIcon) {
                this.props.dial_pad._onClickMinimise()
                icon.classList.remove('ri-phone-fill');
                icon.classList.add('ri-subtract-fill');
                icon.style.fontSize = ''
                icon.style.marginRight = ''
                icon.style.marginBottom = ''
                icon.style.color = 'black';
                icon.classList.add('minimise');
            }
        } else {
            RecentDiv.style.display = 'none';
            closeBtn.style.display = 'none';
            RecentTab.style.minWidth = '50px';
            RecentTab.style.width = '73px';
            RecentTab.style.height = '72px';
            RecentTab.style.borderRadius = '50%';
            RecentTab.style.backgroundColor = '';
            if (minimiseIcon) {
                this.props.dial_pad._onClickMinimise()
                minimiseIcon.classList.add('ri-phone-fill');
                minimiseIcon.classList.remove('ri-subtract-fill');
                minimiseIcon.classList.remove('minimise');
                RecentTab.style.backgroundColor = '#9EA700';
                minimiseIcon.style.color = 'white';
                minimiseIcon.style.fontSize = '32px'
                minimiseIcon.style.marginLeft = '1px'
                minimiseIcon.style.marginBottom = '5px'
            }
        }
    }

    /*To move to the contacts*/
    _OnContacts() {
        this.props.dial_pad.state.recent = false
        this.props.dial_pad.state.contacts = true
    }

    /*To get the contacts*/
    async getRecent(contact) {
        this.state.showPartner = true;
        this.state.selectedPartner = contact;

        if (contact.to_number) {
            const partner = await this.orm.searchRead("res.partner", [
                ["phone", "=", contact.to_number]
            ], ["image_1920", "name"]);
            if (partner.length > 0) {
                // If a partner with this number exists, update the selectedPartner details
                this.state.selectedPartner.image_1920 = partner[0].image_1920;
                this.state.selectedPartner.partner_name = partner[0].name;
            }
        } else if (contact.from_number) {
            const partner = await this.orm.searchRead("res.partner", [
                ["phone", "=", contact.from_number]
            ], ["image_1920", "name"]);
            if (partner.length > 0) {
                // If a partner with this number exists, update the selectedPartner details
                this.state.selectedPartner.image_1920 = partner[0].image_1920;
                this.state.selectedPartner.partner_name = partner[0].name;
            }
        }
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

    /*To make call to the selected partner*/
    async _OnClickCall() {
        device = this.props.dial_pad.device
        this.state.call = true
        var self = this;
        if (this.state.selectedPartner.to_number) {
            this.number = this.state.selectedPartner.to_number
        } else {
            this.number = this.state.selectedPartner.from_number
        }
        const PartnerId = await this.orm.searchRead("res.partner", [
            ["phone", "=", this.number]
        ], ['image_1920', 'name']);

        if (PartnerId && PartnerId.length > 0) {
            this.state.selectedPartner.image_1920 = PartnerId[0].image_1920;
            this.state.selectedPartner.partner_name = PartnerId[0].name;
        }

        if (PartnerId && PartnerId.length > 0) {
            var id = PartnerId[0].id
        } else {
            var id = null
        }
        if (this.number) {
            var params = {
                To: this.number,
            };
            event.stopPropagation();
            if (device) {
                try {
                    const call = await device.connect({
                        params
                    });

                    call.on('ringing', (event) => {
                        const callSid = call.parameters.CallSid;
                        this.sid = callSid
                    });
                    /*
                        Wait for the call to have CallSid
                     */
                    call.on('accept', (event) => {
                        const callSid = call.parameters.CallSid;
                        this.sid = callSid;
                        this.isTimerPaused = false;
                        this._runTimer();
                        this.orm.call('out.going.call.list', 'action_call', [, this.number, callSid, id]);
                    });

                    call.on('cancel', async (event) => {
                        this.state.call = false;
                        this._OnBack()
                        const callSid = call.parameters.CallSid;
                        await this.orm.call('out.going.call.list', 'action_cancel', [, this.number, callSid]);
                        this.action.doAction('soft_reload')
                        this.resetTimer();
                    });

                    call.on('disconnect', async (event) => {
                        this.state.call = false;
                        this._OnBack()
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
                        this._OnBack()
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

    /*
        To create the display notification
    */
    displayNotification(text) {
        this.notification.add(text, {
            type: "warning"
        });
    }

    /*To reject the call*/
    async _onClickCancel() {
        var self = this;
        this.state.call = false;
        this._OnBack()
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
}

RecentTab.template = "recent_tab";
RecentTab.components = {
    ContactTab
}