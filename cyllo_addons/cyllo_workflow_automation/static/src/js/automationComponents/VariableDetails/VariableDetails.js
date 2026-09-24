/** @odoo-module */
import { Component } from "@odoo/owl";
import { icons } from "../../icons"

export class VariableDetails extends Component {
    /**
     * Handles user interactions related to variable details.
     * Provides methods to navigate back, edit, delete, and manage variable-related actions.
     *
     * Props:
     * - `variable` (Object): The variable object containing the variable's details.
     * - `scope` (Object, optional): The scope object related to the variable.
     * - `back` (Function): A callback function to navigate back.
     * - `edit` (Function): A callback function to trigger variable editing.
     * - `delete` (Function): A callback function to trigger variable deletion.
     * - `usedNodes` (Object): The nodes where the variable is used.
     */
    onBack() {
        /**
         * Trigger the back action by calling the `back` function prop.
         */
        this.props.back();
    }

    onEdit() {
        /**
         * Trigger the edit action by calling the `edit` function prop,
         * passing the current `variable` prop to be edited.
         */
        this.props.edit(this.props.variable);
    }

    onDelete() {
        /**
         * Trigger the delete action by calling the `delete` function prop,
         * passing the current `variable` prop to be deleted.
         * Then, call the `back` function to navigate back after deletion.
         */
        this.props.delete(this.props.variable);
        this.props.back();
    }

    getIconSrc(name) {
        /**
         * Retrieve the icon source URL based on the provided icon name.
         *
         * Args:
         * - `name` (string): The name of the icon to retrieve.
         *
         * Returns:
         * - string: The URL or path of the corresponding icon image.
         */
        return icons[name];
    }

    handleClickFind(node) {
        /**
         * Trigger a custom event to find and highlight the node where the variable is used.
         * This triggers the event `FIND:NODE:VARIABLE:USED` with the node's ID.
         *
         * Args:
         * - `node` (Object): The node object containing the data where the variable is used.
         */
        this.env.bus.trigger("FIND:NODE:VARIABLE:USED", {nodeId: node.data.nodeId});
    }
}

VariableDetails.template = 'VariableDetails';
VariableDetails.props = {
    variable: { type: Object },         // The variable details to display
    scope: { type: Object, optional: true },  // The scope, if available (optional)
    back: { type: Function },           // Function to navigate back
    edit: { type: Function },           // Function to edit the variable
    delete: { type: Function },         // Function to delete the variable
    usedNodes: { type: Object },        // Nodes where the variable is used
};
