/** @odoo-module **/
import { Component, xml, onError } from "@odoo/owl";
import { WithEnv } from "../../utils/withenv";


export class DialogContainer extends Component {
    setup() {
        onError(this.handleError);
    }
    handleError(error, dialog) {
        dialog.props.close();
        Promise.resolve().then(() => {
            throw error;
        });
    }
}
DialogContainer.components = { WithEnv };
DialogContainer.template = xml`
    <div class="o_dialog_container" t-att-class="{'modal-open': Object.keys(props.dialogs).length > 0}">
        <div>
            <t t-foreach="Object.values(props.dialogs)" t-as="dialog" t-key="dialog.id">
                <WithEnv env="{ dialogData: dialog.dialogData }">
                    <t t-component="dialog.class" t-props="dialog.props"/>
                </WithEnv>
            </t>
        </div>
    </div>
`;
