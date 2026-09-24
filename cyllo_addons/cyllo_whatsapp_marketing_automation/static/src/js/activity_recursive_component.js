/** @odoo-module **/
import { useService } from "@web/core/utils/hooks";
import { useState, useRef,onMounted, onWillStart, xml, Component } from "@odoo/owl";
import { ActivityRecursiveComponent } from "@cyllo_marketing_automation/js/activity_recursive_component"

export class ActivityRecursiveComponentWhatsapp extends ActivityRecursiveComponent{
    setup() {
        super.setup();
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
            <div t-if="state.status != 'schedule' &amp; props.value.obj.data.type == 'whatsapp'" class="cy-trigger-actions d-flex align-items-center justify-content-between" t-ref='mailStatus'>
                <div class="open cy-test-participation_list-btn"><i class="ri-checkbox-circle-fill"/>OPENED</div>
                <div class="reply cy-test-participation_list-btn"><i class="ri-checkbox-circle-fill"/>REPLIED</div>
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
