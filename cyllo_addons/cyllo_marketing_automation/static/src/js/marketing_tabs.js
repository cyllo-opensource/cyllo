/** @odoo-module **/
import { MarketingChild } from "./marketing_child";
import { useState, useEffect, onWillUpdateProps, useSubEnv} from "@odoo/owl";
export class MarketingTabs extends owl.Component{
    /*
        MarketingTabs component is created to representing marketing tabs.
    */
    setup(){
        // Update active activity when props change
        useEffect(() => {
            this.activeActivity.activity = this.activeTabId ? this.props.activities.filter(activity => activity.id === this.activeTabId)[0] : this.props.activities[0]
        }, () => [this.props])
        this.parentActivity;
        this.subParentActivity;
        this.activeTabId;
        this.activeActivity = useState({ activity: this.props.activities[0] })
        // Sub-environment setup
        useSubEnv({
            activeActivity: this.activeActivity,
            activeTabID:this.activeTabId
        })
        onWillUpdateProps((newProps) => {
            this.activeTabId = this.activeTabId ? newProps.activeTabID : this.activeTabId
        })
    }
    /**
        * Retrieves the sorted values of the respective activities based on their hierarchical structure, considering parent and sub-parent relationships.
        * @returns {Array} - An array of sorted activity objects.
    */
    get sortedValues() {
        const idToObjectMap = {};
        this.respectiveActivities.forEach(obj => {
            idToObjectMap[obj?.id] = obj;
        });
        const rearrangedArray = [];
        let value = 100
        this.respectiveActivities.forEach((obj, index) => {
                obj.h_level = `parent_level_${index}`;
                obj.p_level = '';
                obj.is_parent = false;
                rearrangedArray.push(obj);
            if (obj.sub_parent_activity_id[0] && idToObjectMap[obj.sub_parent_activity_id[0]]) {
                const parentIndex = rearrangedArray.indexOf(idToObjectMap[obj.sub_parent_activity_id[0]]);
                rearrangedArray.pop(index)
                obj.h_level = `child_level`;
                obj.h_level_css = `margin-left: ${value * (parentIndex +1)}px;`;
                rearrangedArray[parentIndex].is_parent = true;
                rearrangedArray.splice(parentIndex + 1, 0, obj);
            }
        });
        return rearrangedArray;
    }
    /**
        * Retrieves the respective activities based on the active activity's parent-child relationship.
    */
    get respectiveActivities() {

            let activeActivity = this.props.allActivities.filter(item => item.parent_activity_id[0] === this.activeActivity.activity.id)
            return [this.activeActivity.activity,...activeActivity]
    }
    /**
        * Retrieves the child data for a given activity object, including the activity itself and its children.
        * @param {Object} obj - The activity object for which child data is retrieved.
        * @returns {Object} - An object containing an array of activity data (including the given activity and its children) and unique IDs.
    */
    getChildData(obj) {
        const data = this.respectiveActivities.filter(item => item.sub_parent_activity_id[0] === obj.id).sort((a,b) => {
            const dateA = new Date(a.create_date);
            const dateB = new Date(b.create_date);
            return dateA - dateB
        })
        const uniqueIds = [obj.id,...data.map( item => item.id )]
        return {
            data: [obj, ...data],
            uniqueIds: uniqueIds
        }
    }
    /**
        * Handles the deletion action by resetting the activeTabId to null.
    */
    handleDelete(){
        this.activeTabId = null;
    }
    /**
        * Retrieves and arranges activity data, ensuring uniqueness based on activity IDs.
        * @returns {Array} An array containing the arranged and unique activity data.
    */
    get activityData() {
        let uniqueId = new Set();
        const rearrangedArray = [];
        this.respectiveActivities.forEach((obj, index) => {
            if (! uniqueId.has(obj.id) ){
                let { data, uniqueIds } = this.getChildData(obj);
                uniqueId.add(...uniqueIds);
                rearrangedArray.push(...data);
            }
        });
        return rearrangedArray;
    }
    /**
        * Handles the click event on an activity tab, updating the active activity and related UI elements.
        * @param {Object} activity - The clicked activity object.
    */
    onClickTab(activity){
        this.activeActivity.activity = activity
        this.activeTabId = activity.id
    }
    /**
        * Handles the click event on an activity, opening a new form view for the selected marketing activity.
        * @param {Object} ev - The click event object.
    */
    onClickActivity(ev){
        let activityId = ev.target.dataset.id;
        this.env.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'marketing.activity',
            views: [[false, 'form']],
            target: 'new',
            res_id: parseInt(activityId),
        })
    }
    /**
        * Handles the click event on an activity, opening a new form view for the selected marketing activity.
        * @param {Object} ev - The click event object.
    */
    handleActivity(ev, props){
        this.parentActivity = this.activeActivity.activity
        this.subParentActivity = props.activity
        let activityDiv = ev.target.parentElement
        let addChildDiv = this.__owl__.bdom.el.querySelector('.child-activity-add-buttons')
        if (activityDiv.classList.contains('selected')){
            activityDiv.classList.remove('selected');
            addChildDiv.style.display = 'none'
        }
        else {
            this.__owl__.bdom.el.querySelectorAll('.child-activities').forEach(element => element.classList.remove('selected'));
            const activityAddButtons = this.__owl__.bdom.el.lastChild.querySelector('.child-activity-add-buttons').querySelectorAll('.active-div');
            const isServer = activityDiv.dataset.type === 'server';
            const isSms = activityDiv.dataset.type === 'sms';
            activityAddButtons.forEach(rec => {
                const isActivityAnother = rec.dataset.trigger === 'activity_another';
                const isMailClick = rec.dataset.trigger === 'mail_click';
                const isMailNotClick = rec.dataset.trigger === 'mail_not_click';
                if ((isServer && !isActivityAnother) || (isSms && !isActivityAnother && !isMailClick && !isMailNotClick)) {
                    rec.classList.add('cy-hide-activityAddButtons');
                } else {
                    rec.classList.remove('cy-hide-activityAddButtons');
                }
            });
            activityDiv.classList.add('selected');
            Object.assign(addChildDiv.style, {
                display: 'flex',
                position: 'sticky',
                top: '0',
                zIndex: '1',
                background: '#F7F7F7',
                width: '50%'
            });
        }
    }
}
MarketingTabs.template = "MarketingTabs"
MarketingTabs.components = {
    MarketingChild,
}
