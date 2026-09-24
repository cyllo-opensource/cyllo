/** @odoo-module **/
import { useService } from "@web/core/utils/hooks";
import { useState, useRef,onMounted, onWillStart, xml, Component } from "@odoo/owl";
export class ActivityRecursiveComponent extends Component{
    /*
        ActivityRecursiveComponent component is created to for managing and displaying recursive activities.
    */
    setup() {
        this.dataSetDateRecords;
        this.isTestParticipant = this.props.participantData.data.is_test_participant
        this.action = useService("action");
        this.orm = useService('orm');
        this.is_inactive = this.props.participantData.data.is_inactive
        this.rootRef = useRef('root')
        this.startButton = useRef('startButton')
        this.cancelButton = useRef('cancelButton')
        this.mainButtonDiv = useRef('mainButtonDiv')
        this.state = useState({
            clicked: false,
            status : this.props.activityLines.data.state,
            totalActivityCount : 0

        });
        /**
            * Lifecycle hook that runs before the component is initialized.
         */
        onWillStart(async () => {
            this.state.totalActivityCount = this.props.participantData.data.activity_ids.count
           const {c: dateTimeObj } = this.props.participantData.data.create_date
            this.parentDate = new Date(
                dateTimeObj.year,
                dateTimeObj.month - 1,
                dateTimeObj.day,
                dateTimeObj.hour,
                dateTimeObj.minute,
                dateTimeObj.second,
                dateTimeObj.millisecond,
            )
            this.triggerType = this.props.value.obj.data.activity_trigger_type
            this.triggerVal = this.props.value.obj.data.activity_trigger
            this.changeTime()
        })
        /**
            * Lifecycle hook that runs after the component is mounted.
         */
        onMounted(async() => {
            const addTrackedClass = (element, condition, className) => {
                if (condition) {
                    let trackedElement = element.querySelector(className);
                    trackedElement.classList.add('cy-tracked-div');
                }
            };
            if (this.parentObject && this.parentObject.data.state ==="schedule") {
                this.rootRef.el.classList.add("cy-hideMain-div")
            }
            // Assuming __owl__.refs.mailStatus is your main container element
            const mailStatusContainer = this.__owl__.refs.mailStatus;
            addTrackedClass(mailStatusContainer, this.props.activityLines.data.mail_clicked, '.click');
            addTrackedClass(mailStatusContainer, this.props.activityLines.data.mail_opened, '.open');
            addTrackedClass(mailStatusContainer, this.props.activityLines.data.mail_replied, '.reply');
            addTrackedClass(mailStatusContainer, this.props.activityLines.data.mail_bounced, '.bounce');
            var inactiveStatus = await this.orm.searchRead("marketing.participant",[['id','=',this.props.participantData.resId]],['is_inactive'])
            if(this.state.status != 'schedule'){
                if (this.__owl__?.refs?.mainButtonDiv) {
                    this.__owl__.refs.mainButtonDiv.style.display = 'none';
                }
                    var nextButtonDiv = this.__owl__.bdom.parentEl.querySelectorAll('[data-parent_activity="' + (this.props.value.obj.resId) + '"]')
            }
        })

    }
    get parentObject() {
    /**
        * Retrieves the parent object based on the sub-parent activity ID.
        * @returns {Object | undefined} The parent object or undefined if not found.
    */
        const { sub_parent_activity_id: subParentId } = this.props.value.obj.data
        return this.props.data.find(item => item.data.activity_id[0] === subParentId[0])
    }
    changeTime() {
    /**
        * Change the time of the parent date based on the specified trigger type and value.
        * @param {void}
    */
        switch(this.triggerType) {
            case "hour":
                // Increment hours in the parent date
                this.parentDate.setHours(this.parentDate.getHours() + this.triggerVal);
                break;
            case "week":
                // Increment days in the parent date based on weeks
                this.parentDate.setDate(this.parentDate.getDate() + (this.triggerVal * 7));
                break;
            case "month":
                // Increment months in the parent date
                this.parentDate.setMonth(this.parentDate.getMonth() + this.triggerVal);
                break;
            case "day":
                // Increment days in the parent date
                this.parentDate.setDate(this.parentDate.getDate() + this.triggerVal);
                break;
        }
    }
    /**
        * Handle the click event for the send button asynchronously.
        * Extract necessary data, update participant records using the Odoo ORM, and trigger a 'click_send' event.
        * @param {Object} ev - The event object.
    */
     async onClickSendButton(ev){
        // Access the parent element of the clicked button
        var parentElement = ev.target.parentElement.parentElement.parentElement
        // Prepare data for the Odoo ORM call
        let data = {
            participant_id : this.props.participantData.resId,
            activity_id : this.props.value.obj.resId,
            test : this.props.participantData.data.is_test_participant,
            activity_line : this.props.activityLines.resId
        }
        // Call the Odoo ORM to update participant records asynchronously
        let updatedRecord = await this.orm.call('marketing.participant', 'update_record', [data]).then((data) => {
            // Trigger a soft reload action
            this.action.doAction('soft_reload')
        })
        // Trigger a 'click_send' event after updating records
        this.env.bus.trigger('click_send',{})
    }
    /**
        * Handle the click event for the cancel button.
        * Update the state of the activity lines to 'cancel' and set the component's status to 'cancel'.
    */
    onClickCancelButton(){
        // Update the state of the activity lines to 'cancel'
        this.props.activityLines.update({'state':'cancel'})
        // Set the component's status to 'cancel'
        this.state.status = 'cancel'
    }
    /**
        * Set the date using the provided data dictionary and return the formatted date string.

        * @param {Object} data - The dictionary containing date components (day, hour, minute, month, year).
        * @returns {string} - The formatted date string (YYYY-MM-DD HH:mm:ss).
    */
    setDateFromDictionary(data) {
        // Extract data from the dictionary
        const { day, hour, minute, month, year } = data;
        // Create a new Date object with the extracted data
        const newDate = new Date(year, month, day, hour, minute);
        // Format date components
        var monthNew = ('0' + (newDate.getMonth() + 1)).slice(-2);
        var dayNew = ('0' + newDate.getDate()).slice(-2);
        var hoursNew = ('0' + newDate.getHours()).slice(-2);
        var minutesNew = ('0' + newDate.getMinutes()).slice(-2);
        var secondsNew = ('0' + newDate.getSeconds()).slice(-2);
        // Create the formatted date string
        var formattedDate = year + '-' + monthNew + '-' + dayNew + ' ' + hoursNew + ':' + minutesNew + ':' + secondsNew;
        // Return the formatted date string
        return formattedDate;
    }
    /**
        * Get the trigger date by converting date components from the parentDate property.

        * @returns {Object} - An object representing the formatted date components (day, hour, minute, month, year).
    */
    get triggerDate() {
        // Get the date components from the parentDate property
        const record = this.parentDate
        // Create an object with date components
        const data = {
            day: record.getDate(),
            hour: record.getHours(),
            minute: record.getMinutes(),
            month: record.getMonth(),
            year: record.getFullYear()
        };
        // Call the setDateFromDictionary function to format the date components
        const dateObject = this.setDateFromDictionary(data);
        // Return the formatted date object
        return dateObject
    }
    /**
        * Convert a record's date components into a formatted date using the setDateFromDictionary function.

        * @param {Object} record - The record containing date components (day, hour, minute, month, year).
        * @returns {string} - The formatted date string.
    */
    dataSetDateRecords(record){
        // Extract date components from the provided record
        const data = {
            day: record.day,
            hour: record.hour,
            minute: record.minute,
            month: record.month,
            year: record.year
        };
        // Call the setDateFromDictionary function to format the date
        return this.setDateFromDictionary(data);
    }
    /**
        * Convert a state key to its corresponding human-readable value.

        * @param {string} values - The state key to be converted.
        * @returns {string} - The human-readable value associated with the state key.
    */
    stateKey(values){
        // Mapping of state keys to human-readable values
        var selectionValues = {
            'schedule': 'SCHEDULED',
            'cancel': 'CANCELLED',
            'reject': 'REJECTED',
            'processed': 'PROCESSED',
            'error':'ERROR',
            'begin':'Beginning of Workflow',
            'activity_another':'Another Activity',
            'mail_open':'Mail: Opened',
            'mail_not_open':'Mail: Not Opened',
            'mail_reply':'Mail: Replied',
            'mail_not_reply':'Mail: Not Replied',
            'mail_click':'Mail: Clicked',
            'mail_not_click':'Mail: Not Clicked',
            'mail_bounce':'Mail: Bounced',
            'hour':'Hour',
            'day':'Day',
            'week':'Week',
            'month':'Month'
        };
        // Get the human-readable value associated with the state key
        var value = selectionValues[values];
        // Return the human-readable value
        return value
    }
    /**
        * Get the activity ID from the provided data array.

        * @param {Array} data - The array containing data items.
        * @returns {Object} - The first item in the array.
    */
    getActivityId(data){
        data.forEach(item => {
            return item
        })
    }

}
//ActivityRecursiveComponent.template = "ActivityRecursiveComponent"
ActivityRecursiveComponent.template = xml`
    <div class=" mainDiv-component cy-marketing-auto_list-box-test" t-ref="root" t-att-class="props.participantData.data.is_test_participant ?'add-min':''"
         t-att-style="props.value.css" t-att-data-parent_activity="props.value.obj.data.sub_parent_activity_id[0]">
            <div class="header-component  cy-border-btm p-2 gap-4">
                <div class="d-flex align-items-center gap-2">
                    <button t-if="props.value.obj.data.type == 'mail' &amp; state.status != 'schedule'" class="mail headAction cy-marketing-auto_icon-btn cy-marketing-auto_mail-icon">
                        <i class="ri-mail-open-line" />
                    </button>
                    <button t-if="props.value.obj.data.type == 'mail' &amp; state.status == 'schedule'" class="mail headAction cy-marketing-auto_icon-btn cy-marketing-auto_mail-icon">
                        <i class="ri-time-line" />
                    </button>
                    <button t-if="props.value.obj.data.type == 'server' &amp; state.status != 'schedule'" class="server headAction cy-marketing-auto_icon-btn cy-marketing-auto_mail-icon">
                        <i class="ri-git-merge-line"/>
                    </button>
                    <button t-if="props.value.obj.data.type == 'server' &amp; state.status == 'schedule'" class="server headAction cy-marketing-auto_icon-btn cy-marketing-auto_mail-icon">
                        <i class="ri-time-line"/>
                    </button>
                    <div class="cy-activity-details_div">
                        <div class="cy-status-tag d-flex align-items-center">
                            <p class="cy-headName cy-marketing_auto-box_title mb-0" t-out="props.value.obj.data.name" t-att-title="props.value.obj.data.name"/>
                            <span t-att-class="{'processed': state.status == 'processed','schedule': state.status == 'schedule','cancel': state.status == 'cancel','error': state.status == 'error'}" class="cy-test_participation-tree_box-label" t-out="stateKey(state.status)"/>
                        </div>
                        <div class="cy-marketing_auto-box-subtitle d-flex align-items-center">
                            <span class="d-flex align-items-center gap-2">
                                <i t-if="props.value.obj.data.type == 'mail'" class="ri-mail-open-line"/>
                                <i t-if="props.value.obj.data.type == 'server'" class="ri-git-merge-line"/>
                                <t t-out="props.value.obj.data.type"/>
                            </span>
                            <span class="px-1">.</span>
                            <span t-out="triggerDate" class="cy_date-class"/>
                        </div>
                    </div>
                    <div t-if="props.activityLines.data.state == 'schedule'" class="cy-mainDiv_buttons d-flex align-items-center gap-2" t-ref="mainButtonDiv">
                        <button class="start_button cy-marketing-auto_icon-btn cy-marketing-auto_edit-icon cy-active-btn" title="Run" t-on-click="onClickSendButton" t-att-data-state="state.status" t-ref="startButton" t-att-data-activity="props.value.obj.resId">
                            <i class="ri-play-line"/>
                        </button>
                        <button class="cancel_button cy-marketing-auto_icon-btn cy-marketing-auto_delete-icon " title="Cancel" t-on-click="onClickCancelButton" t-ref="cancelButton">
                            <i class="ri-close-line"/>
                        </button>
                    </div>
                </div>
                <p class="cy-marketing_auto-box-subtitle m-0 my-1" t-out="props.activityLines.data.mail_failure_message"/>
            </div>
            <div t-if="state.status != 'schedule' &amp; props.value.obj.data.type == 'mail'" class="cy-trigger-actions d-flex align-items-center justify-content-between" t-ref='mailStatus'>
                <div class="open cy-test-participation_list-btn"><i class="ri-checkbox-circle-fill"/>OPENED</div>
                <div class="click cy-test-participation_list-btn"><i class="ri-checkbox-circle-fill"/>CLICKED</div>
                <div class="reply cy-test-participation_list-btn"><i class="ri-checkbox-circle-fill"/>REPLIED</div>
                <div class="bounce cy-test-participation_list-btn"><i class="ri-checkbox-circle-fill"/>BOUNCED</div>
            </div>
         <div class="cy_trigger-details-div cy-marketing-auto_timing-test cy-test_participation-timing">
             <div>
                <span class="cy_icon-style-marketing"><i class="ri-time-line"/></span>
                <span>
                    <span><t t-out="props.value.obj.data.activity_trigger"/></span>
                    <span class="px-1"><t t-out="stateKey(props.value.obj.data.activity_trigger_type)"/></span>
                </span>
             </div>
            <span class="cy-schedule-type" t-out="stateKey(props.value.obj.data.trigger_schedule_type)"/>
         </div>
    </div>`
