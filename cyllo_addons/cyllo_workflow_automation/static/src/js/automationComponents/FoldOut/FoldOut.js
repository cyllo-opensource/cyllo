/** @odoo-module */

import { Component, useState } from "@odoo/owl";

export class FoldOut extends Component {
    /**
     * A component that provides collapsible/expandable content functionality.
     *
     * The `FoldOut` component allows you to toggle between showing and hiding
     * content, with an initial state that can be controlled through the `defaultExpanded` prop.
     *
     * Props:
     * - `title` (String): The title or label displayed for the fold-out section.
     * - `defaultExpanded` (Boolean, optional): Determines if the content is expanded by default.
     *   If not provided, defaults to `false`.
     * - `slots`: The default slot for placing the content inside the fold-out component.
     *
     * Methods:
     * - `setup()`: Initializes the component state, setting the `expanded` state based on the `defaultExpanded` prop.
     * - `toggleExpand()`: Toggles the expanded/collapsed state of the component.
     *
     * Template:
     * The component is rendered using the 'FoldOut' template.
     */
    setup() {
        this.state = useState({
            expanded: this.props.defaultExpanded || false
        });
    }

    toggleExpand() {
        this.state.expanded = !this.state.expanded;
    }
}

FoldOut.template = 'FoldOut';
FoldOut.props = {
    title: String, defaultExpanded: {type: Boolean, optional: true}, slots: {
        default: true
    }
};