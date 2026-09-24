/** @odoo-module **/
import { Component, xml} from "@odoo/owl";

export class ErrMessage extends Component {
    /**
     * ErrMessage component displays an error message with an information icon.
     */
}

ErrMessage.template = xml`
    <span style="color:#f2a033">
        <i class="ri-information-line"/>
        <t t-out="props.message"/>
    </span>
`;

ErrMessage.props = {
    /**
     * The message to be displayed as an error.
     * @type {String}
     */
    message: String,
};