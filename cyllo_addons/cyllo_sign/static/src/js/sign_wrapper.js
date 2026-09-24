/** @odoo-module **/
import { Component, xml, useState, useRef } from '@odoo/owl';
import { SignConfigureAction } from './sign_configure/sign_configure';
import { jsonrpc } from "@web/core/network/rpc_service";

export default class SignWrapper extends Component {
    static template = xml`
        <t t-if="state.loading">
            <div>Loading...</div>
        </t>
        <t t-else="">
            <t t-component="signComponent" t-props="signProps"/>
        </t>
    `;
    setup() {
        const currentUrl = window.location.href;
        const url = new URL(currentUrl);
        this.queryParams = Object.fromEntries(url.searchParams.entries());
        this.state = useState({
            roleData: null,
            loading: true,
        });
        this.fetchRoles();
    }
    get signComponent() {
        return SignConfigureAction;
    }
    async fetchRoles() {
        try {
            const role_data = await jsonrpc('/web/dataset/call_kw/sign.request/get_roles', {
                model: 'sign.request', method: 'get_roles',
                args: [parseInt(this.queryParams.request_id)],
                kwargs: {},
            });
            this.state.roleData = role_data.map(role => role.role_id[0]);
        } catch (error) {
            console.error('Error fetching roles:', error);
        } finally {
            this.state.loading = false;
        }
    }
    get signProps() {
        return this.queryParams.res_id ? {
            res_id: parseInt(this.queryParams.res_id),
            request_id: parseInt(this.queryParams.request_id),
            res_model: this.queryParams.res_model,
            partner_id: this.queryParams.partner_id,
            requester_ids: this.queryParams.requester_ids,
            portal: true,
            mail: this.queryParams.mail || false,
            roles: this.state.roleData
        } : {};
    }
}