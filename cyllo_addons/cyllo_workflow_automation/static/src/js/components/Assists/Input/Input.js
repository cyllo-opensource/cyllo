/** @odoo-module */

import { Component } from "@odoo/owl";


export default class RealTimeInput extends Component {
    /**
     * RealTimeInput is a component that handles real-time input updates.
     * It allows for immediate updates to the input value as the user types.
     */
    /**
     * Properties:
     * - value: The current value of the input.
     * - update: A function to call when the input value changes.
     * - startEmpty (optional): A boolean indicating if the input should start empty.
     */
    static props = ["value", "update", "startEmpty?"];
    static template = "RealTimeInput";
}