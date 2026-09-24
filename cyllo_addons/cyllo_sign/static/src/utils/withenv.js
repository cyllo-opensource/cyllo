/** @odoo-module **/
import { Component, xml, useSubEnv } from "@odoo/owl";


export class WithEnv extends Component {
    setup() {
        useSubEnv(this.props.env);
    }
}
WithEnv.template = xml`<t t-slot="default"/>`;
