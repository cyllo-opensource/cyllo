/** @odoo-module **/
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Many2OneField } from "@web/views/fields/many2one/many2one_field";
import {useBus } from "@web/core/utils/hooks";
import { ActivityRecursiveComponent } from "./activity_recursive_component"
const { useRef, useState, mount } = owl;
export class ActivityTest extends Many2OneField {
    /*
        ActivityTest component is created to extends Many2OneField.
    */
    setup() {
        super.setup();
        this.arrangeOrder() // Arrange the order of activities
        this.root = useRef('root') // Reference to the root element
        useBus(this.env.bus, 'click_send', (ev) => {
            this.computeActivityCount(ev) // Update activity count on 'click_send' event
        })
        var mainData = this.props.arrangedData.slice()
        owl.onMounted(() => this.MountChild(mainData)) // Mount child components on component mount
        this.state =  useState({
            totalActivityCountRunning:this.props.record.data.record_count,
            arrangedData: this.props.arrangedData
        })
    }
    /**
        * Decreases the total activity count and updates the record.
        * If the total activity count reaches zero, updates the record state to 'completed'.
        * @param {Event} ev - The event object.
    */
    computeActivityCount(ev){
        this.state.totalActivityCountRunning --
        this.props.record.update({'record_count': this.state.totalActivityCountRunning})
        if(this.state.totalActivityCountRunning == 0){
            this.props.record.update({'state':'completed'})
        }
    }
    /**
        * Returns the records data for the specified property name from the component's props.
        * @returns {Array} - The records data.
    */
    get recordData () {
        return this.props.record.data[this.props.name].records
    }
    /**
        * Returns the activity IDs for a given participant's resId from the component's props.
        * @param {number} resId - The resId of the participant.
        * @returns {Array} - The activity IDs.
    */
    getActivityIds(resId) {
        return this.props.record.data.activity_ids.records.filter(item => item.resId === resId)
    }
    /**
        * Returns the participant data from the component's props.
        * @returns {Object} - The participant data.
    */
    get participantData(){
        return this.props.record
    }
    /**
        * Returns the activity lines from the component's props.
        * @returns {Array} - An array of activity lines.
    */
    get activityLines(){
            return this.props.record.data.test_activity_ids.records
    }
    get Records() {
        return this.props.record.data.activity_ids.records
    }
    /**
        * Returns the records from the component's props.
        * @returns {Array} - An array of records.
    */
    get AllParentRecords() {
        return this.Records.filter(item => !item.data.parent_activity_id)
    }
    /**
        * Retrieves a hierarchical structure of child activities based on the specified parent.
        * @param {Object} parent - The parent activity.
        * @returns {Object} - The hierarchical structure of child activities.
    */
    getChild(parent) {
        const parentId = parent.resId/* Your specified parent id */;
        const records = this.Records.filter(item => item.data.parent_activity_id[0] === parentId);
        /**
            * Builds the hierarchy recursively for the specified parent id.
            * @param {Array} records - An array of records.
            * @param {number} parentId - The parent id for which the hierarchy is built.
            * @param {number} index - The index for positioning the children.
            * @returns {Array} - The hierarchical structure of child activities.
        */
        const buildHierarchy = (records, parentId, index) => {
            let result = [];
            index ++
            for (const record of records) {
                if (record.data.sub_parent_activity_id[0] === parentId) {
                    const children = buildHierarchy(records, record.resId, index);
                    result.push({ id: record.resId,obj: record,name:record.data.name,children: children, css:`transform: translateX(${130 * index}px);` });
                }
            }
            return result;
        };
        // Assuming parentId is the specified parent id
        const hierarchy = { id: parentId,obj: parent,name:parent.data.name,css:"", children: buildHierarchy(records, parentId, 0) };
        /**
            * Filters data based on the specified parent id.
            * @param {number} parentId - The parent id.
            * @returns {Array} - An array of filtered records.
        */
        const filterData = (parentId) => {
            return records.filter(item => item.data.sub_parent_activity_id[0] === parentId)
        }

        let resParentId = 0
        records.forEach((item, i) => {
            resParentId = resParentId === 0 ? item.data.sub_parent_activity_id[0] : resParentId
            let value = filterData(resParentId)?.value || 1
            if(item.data.sub_parent_activity_id[0] > resParentId) {
                value ++
                resParentId = item.data.sub_parent_activity_id[0]
            }
            item.value = value
            item.data.h_level_css = `transform: translateX(${130 * value}px);`;
        })
        return hierarchy
    }
    /**
        * Arranges the order of hierarchical data based on parent-child relationships.
    */
    arrangeOrder(){
        let finalData = []
        let finalHierarchy = []
        // Iterate through all parent records to build the hierarchical structure
        for( const parent of this.AllParentRecords) {
            finalHierarchy.push(this.getChild(parent))
        }
          // Set the arranged hierarchical data to the component's property
          this.props.arrangedData = finalHierarchy;
    }
    /**
        * Returns the arranged hierarchical data for rendering.
        * @returns {Array} The arranged hierarchical data.
    */
    get arrangedFinalData() {
        return this.props.arrangedData
    }
    /**
        * Mounts child components recursively based on the provided data.
        * @param {Array} data - The data for which child components should be mounted.
        * @returns {Promise<void>} A promise that resolves when the mounting process is complete.
    */
    async MountChild(data) {
        for (const value of data){
            await mount(ActivityRecursiveComponent,this.root.el, {
                props: {
                value,
                data: this.recordData,
                participantData: this.participantData,
                activityLines: this.recordData.find(item => item.data.activity_id[0] === value.id )
                },
                env: this.env
            }).then(async () => {
                if (value.children.length){
                await this.MountChild(value.children)
            }
            })
        }
    }
}
ActivityTest.template = 'TestActivity';
ActivityTest.components = {
    ActivityRecursiveComponent
}
ActivityTest.props = {
    ...standardFieldProps,
};
export const activityTest = {
    component: ActivityTest,
};
registry.category("fields").add("TestActivity", activityTest);
