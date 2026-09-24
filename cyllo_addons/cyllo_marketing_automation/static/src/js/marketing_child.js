/** @odoo-module **/
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { useService } from "@web/core/utils/hooks";

export class MarketingChild extends owl.Component{
    /*
        MarketingChild component is created to representing a marketing child.
    */
    setup(){
        this.dialogService = useService('dialog');
        this.orm = useService("orm");
        this.action = useService("action");
    }
    /**
        * Handles the click event on the activity, triggering the specified action with the provided data.
        *
        * @param {Event} ev - The click event.
    */
    onClickSelectActivity(ev){
        this.props.handleActivity(ev, this.props)
    }
    /**
        * Handles the click event on the activity, opening a new form view for the selected marketing activity.
    */
    async onClickActivity(){
        if (this.props.edit){
            let campaignId = this.props.activity.campaign_id[0]
            let campaignStatus = await this.orm.searchRead("marketing.campaign", [["id", "=", campaignId]], ["state"])
            this.env.action.doAction({
                type: 'ir.actions.act_window',
                res_model: 'marketing.activity',
                views: [[false, 'form']],
                target: 'new',
                res_id: this.props.activity.id,
            },{
                onClose: (ev) => {
                        this.env.bus.trigger('REFRESH-DATA', {activity:this.props.activity.parent_activity_id ? this.props.activity.parent_activity_id[0] : this.props.activity.id})
                },
            });
        }
    }
    /**
        * Asynchronously confirms the deletion of the marketing activity by unlinking it and triggering a data refresh event.
    */
    async confirm(){
        await this.env.orm.call('marketing.activity','unlink',[[this.props.activity.id]]);
        if(this.props.activity.parent_activity_id == false){
            this.action.doAction('soft_reload')
        }
        else{
            this.env.bus.trigger('REFRESH-DATA',{activity:this.props.activity.parent_activity_id ? this.props.activity.parent_activity_id[0] : false})
        }

    }
    /**
        * Handles the click event to delete the marketing activity. If the activity is a parent, it triggers a confirmation dialog, and upon confirmation, it deletes the activity and its children.
        * If the activity is not a parent, it directly deletes the activity.
        * @param {Object} ev - The click event.
    */
    async onClickDeleteRecord(ev){
        if (this.props.edit){
            if (this.props.activity.is_parent){
                this.env.bus.trigger('ADD-DIALOGUE',{
                    class: ConfirmationDialog,
                    props: {
                        body: "Are You Sure?, Deleting this activity will delete all its children activities.",
                        confirm: this.confirm.bind(this),
                        cancel: () => {}
                    }
                })
            }
            else this.confirm()
        }
    }
    stateKey(values){
        var selectionValues = {
            'begin':'Beginning of Workflow',
            'activity_another':'Another Activity',
            'mail_open':'Mail: Opened',
            'mail_not_open':'Mail: Not Opened',
            'mail_reply':'Mail: Replied',
            'mail_not_reply':'Mail: Not Replied',
            'mail_click':'Mail: Clicked',
            'mail_not_click':'Mail: Not Clicked',
            'mail_bounce':'Mail: Bounced',
            'hour': 'Hours',
            'day': 'Days',
            'week': 'Weeks',
            'month': 'Months',
        };
        var value = selectionValues[values];
        return value
    }
    /**
        * Handles the selection of a marketing activity, displaying or hiding child activity add buttons accordingly.
        * @param {Object} ev - The click event object.
        * @param {Object} props - The properties object containing information about the clicked activity.
    */
    async onClickAddActivityDiv(ev){
        if(this.props.edit){
            let node = ev.target.tagName === 'I' ? ev.target.closest('.active-div') : ev.target.parentElement
            let activityDiv = node.offsetParent
            this.env.action.doAction({
                type: 'ir.actions.act_window',
                res_model: 'marketing.activity',
                views: [[false, 'form']],
                target: 'new',
                context: {
                    'default_campaign_id': this.env.context.active_id,
                    'default_trigger_schedule_type':node.dataset.trigger,
                    'default_parent_activity_id': this.env.activeActivity.activity.id,
                    'default_sub_parent_activity_id':parseInt(activityDiv.dataset.id)
                }
            },{
                onClose: (ev) => {
                    this.env.bus.trigger('REFRESH-DATA', {activity:this.props.activity.parent_activity_id ? this.props.activity.parent_activity_id[0] : this.props.activity.id})
                }
            });
        }
    }
}
MarketingChild.template = "MarketingChild"