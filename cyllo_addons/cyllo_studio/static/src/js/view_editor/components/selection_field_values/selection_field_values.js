/** @odoo-module **/
import { Component, useState, useEffect, useRef } from "@odoo/owl";
import { SelectionFieldValue } from "@cyllo_studio/components/selection_field_value_widget";


/**
 * SelectionFieldValues
 *
 * Component for managing selection-type field values in Odoo Studio.
 * Provides functionality to:
 *  - Display selection values
 *  - Drag-and-drop reorder values
 *  - Add, edit, and delete values
 *  - Validate values to avoid duplicates or empty entries
 *
 * Props:
 *  - values: Array of initial selection values
 */
export class SelectionFieldValues extends Component {

    setup() {
        this.state = useState({
            selectionValues: this.props.values,
        });
        this.selectionValuesRef = useRef('cy-SelectionValues')
        useEffect(() => {
            const self = this
            var drake = dragula([this.selectionValuesRef.el], {
                revertOnSpill: true,
                moves: (el, container, handle) => {
                    return handle.classList.contains('handle-drag');
                },
            }).on('drop', function (el, target, source, sibling) {

                let selectionValuesArr = self.state.selectionValues

                let currentIndex = el.getAttribute("data-index")
                let currentValue = selectionValuesArr[currentIndex]
                let targetIndex = sibling ? sibling.getAttribute("data-index") - 1 : selectionValuesArr.length - 1

                self.state.selectionValues = selectionValuesArr.map((element, index) => {
                    if (index >= currentIndex && index <= targetIndex) {
                        return index == targetIndex ? currentValue : selectionValuesArr[index + 1]
                    }
                    return element
                });

                this.cancel();
            });
        }, () => [this.state.selectionValues])
    }

    checkSelectionValues() {
        const lowerCaseArray = this.state.selectionValues.map(element => element.toLowerCase());
        let setValues = new Set(lowerCaseArray);
        const isSameElement = setValues.size != lowerCaseArray.length
        const isEmpty = lowerCaseArray.some(str => str === null || str.match(/^ *$/) !== null);
        if (isSameElement || isEmpty) {
            let message = isSameElement ? 'Containing same values!' : 'Containing empty values!'
            this.env.services.action.doAction({
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': message,
                    'type': 'warning',
                    'sticky': false,
                }
            })
            return false
        }
        return true
    }

    addSelectionValue() {
        return this.checkSelectionValues() ? this.state.selectionValues.push('') : false
    }
    changeSelectionValue(index, value) {
        this.state.selectionValues[index] = value
    }
    deleteSelectionValue(index) {
        this.state.selectionValues.splice(index, 1)
    }
}

SelectionFieldValues.template = "cyllo_studio.SelectionFieldValues"
SelectionFieldValues.components = { SelectionFieldValue }