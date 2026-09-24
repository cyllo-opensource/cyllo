/** @odoo-module **/
import { Component, useState, xml } from "@odoo/owl";


export class TextInputDialog extends Component {
    setup() {
        this.state = useState({
            value: this.props.defaultValue || "",
        });
    }
    // Method to handle input changes
    onInput(event) {
        this.state.value = event.target.value;
    }
    // Method to confirm and send back the value
    onConfirm() {
        if (this.props.onConfirm) {
            this.props.onConfirm(this.state.value);
        }
        this.trigger('close'); // Close the dialog
    }
    // Method to cancel the input
    onCancel() {
        this.trigger('close'); // Close the dialog
    }
    static template = xml`
        <div class="modal fade show d-block">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title"><t t-esc="props.label || 'Input Required'" /></h5>
                        <button type="button" class="btn-close" aria-label="Close" t-on-click="onCancel"></button>
                    </div>
                    <div class="modal-body">
                        <input
                            type="text"
                            class="form-control"
                            t-att-placeholder="props.placeholder || ''"
                            t-att-value="state.value"
                            t-on-input="onInput"
                        />
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" t-on-click="onCancel">Cancel</button>
                        <button type="button" class="btn btn-primary" t-on-click="onConfirm">Confirm</button>
                    </div>
                </div>
            </div>
        </div>
    `;
}
