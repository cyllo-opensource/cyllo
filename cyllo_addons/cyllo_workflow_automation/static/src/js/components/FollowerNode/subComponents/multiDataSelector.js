/** @odoo-module */
const { useState, Component, useEffect, onWillStart } = owl;
//import {ConfigurationBase} from "../configurationBase/configurationBase";
import {Dropdown} from "@web/core/dropdown/dropdown";
import {DropdownItem} from "@web/core/dropdown/dropdown_item";
import { FieldTypeDropdown} from "../../Assists/fieldTypeDropdown/fieldTypeDropDown";

export class MultiDataSelector extends Component {

     changeFieldType(type) {
        this.props.toggleIncludeVariable(type,this.props.index)
     }
     insertData(plus){
         plus?this.props.add(this.props.index):this.props.add();
     }
    getValueEditorInfo(){
        return this.props.getValueEditorInfo(this.props.getDataValue)
    }
     setAddFollowerData(value) {
        this.props.setData(value,this.props.index)
     }
     removeAddFollower(){
        this.props.removeData(this.props.index)
     }
     getDropdownLabel(selectionType) {
        const labels = {
            static: 'Fixed',
            variable: 'Variable',
            record: 'Record',
        };
        return labels[selectionType] || 'Fixed';
    }
}
MultiDataSelector.template = "multiDataSelector";
MultiDataSelector.components = { Dropdown,DropdownItem, FieldTypeDropdown }