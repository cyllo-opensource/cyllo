/** @odoo-module **/
import { Component, useEffect, useState } from "@odoo/owl";
import { FloatTimeField } from "@web/views/fields/float_time/float_time_field";

export class GridFloatTimeField extends Component {
    /*
        GridFloatTimeField component is created to
        customize the FloatTimeField component
    */
    setup(){
        this.editedRecords = useState({ records : [] })
        /*
            In this hook is used to take the timer in each count
        */
        useEffect((el)=>{
            this.editedRecords.records.data.unit_amount = this.props.time
        },() => [this.props.time])

    }
    /*
        Function to get the properties of FloatTimeField component
    */
   get FloatTimeFieldProps(){
        this.editedRecords.records = this.props.record
        return {
            record : this.editedRecords.records || this.props.record,
            name : this.props.name,
            displaySeconds : this.props.displaySeconds,
            readonly : this.props.readonly
        }
    }
}
GridFloatTimeField.template = 'cyllo_timesheet_grid.GridFloatTimeField'
GridFloatTimeField.components = {
    FloatTimeField
}
GridFloatTimeField.props = {
    record : { type : Object , optional: false },
    name : { type : String , optional: true },
    readonly : { type : Boolean , optional: true },
    displaySeconds : { type : Boolean , optional: true },
    time : { type : Number , optional: true },
}
GridFloatTimeField.defaultProps = {
    displaySeconds : true
}
