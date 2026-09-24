/** @odoo-module **/
import { registry } from "@web/core/registry";
import { CharField, charField } from '@web/views/fields/char/char_field';
import { useRef } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
export class AddressAutofill extends CharField {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.orm = useService("orm");
        this.zipInput = useRef("input");
    }
    async AutoFill() {
        const coordinates = await this.geocodeAddress();

        if (coordinates) {
            const latitude = coordinates['lat'];
            const longitude = coordinates['lon'];
            this.fetchAddressDetails(latitude, longitude)
        } else {
            this.actionService.doAction({
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': 'Failed to fetch coordinates for the provided address.',
                    'type': 'warning',
                }
            });
        }
    }
    async fetchAddressDetails(latitude, longitude) {
        try {
            const url = `https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${latitude}&lon=${longitude}&zoom=18&addressdetails=1`;
            const response = await fetch(url);
            const data = await response.json();
            const name = data.address['village'] || data.address['town'] || data.address['neighbourhood'] || data.address['road'] || data.address['name'] || '';
            const pin_code = data.address['postcode'] || '';
            const city = data.address['city'] || '';
            const country = await this.orm.searchRead("res.country", [
                ['name', '=', data.address['country']]
            ], ['name', 'id']);
            const state = await this.orm.searchRead("res.country.state", [
                ['name', '=', data.address['state']]
            ], ['name', 'id']);
            if (this.props.record.resModel == 'hr.employee') {
                this.props.record.data.private_street = name
                this.props.record.data.private_zip = pin_code
                this.props.record.data.private_city = city
                this.props.record._changes.private_street = name
                this.props.record._changes.private_zip = pin_code
                this.props.record._changes.private_city = city
                if (country.length > 0) {
                    this.props.record.data.private_country_id = [country[0].id, country[0].name]
                    this.props.record._changes.private_country_id = [country[0].id, country[0].name]
                } else {
                    this.props.record.data.private_country_id = false
                    this.props.record._changes.private_country_id = false
                }
                if (state.length > 0) {
                    this.props.record.data.private_state_id = [state[0].id, state[0].name]
                    this.props.record._changes.private_state_id = [state[0].id, state[0].name]
                } else {
                    this.props.record.data.private_state_id = false
                    this.props.record._changes.private_state_id = false
                }
            } else {
                this.props.record.data.street = name
                this.props.record.data.zip = pin_code
                this.props.record.data.city = city
                this.props.record._changes.street = name
                this.props.record._changes.zip = pin_code
                this.props.record._changes.city = city
                if (country.length > 0) {
                    this.props.record.data.country_id = [country[0].id, country[0].name]
                    this.props.record._changes.country_id = [country[0].id, country[0].name]
                } else {
                    this.props.record.data.country_id = false
                    this.props.record._changes.country_id = false
                }
                if (state.length > 0) {
                    this.props.record.data.state_id = [state[0].id, state[0].name]
                    this.props.record._changes.state_id = [state[0].id, state[0].name]
                } else {
                    this.props.record.data.state_id = false
                    this.props.record._changes.state_id = false
                }
            }
            this.props.record.dirty = true
            // Handle other details as needed
        } catch (error) {
            this.actionService.doAction({
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': error,
                    'type': 'warning',
                }
            });
        }
    }
    async geocodeAddress() {
        const url = 'https://nominatim.openstreetmap.org/search';
        const pay_load = {
            limit: 1,
            format: 'json',
            street: '',
            postalcode: this.zipInput.el.value || '',
            city: '',
            state: '',
            country: '',
        };
        try {
            const response = await fetch(`${url}?${new URLSearchParams(pay_load)}`);
            const data = await response.json();
            return data.length > 0 ? data[0] : null;
        } catch (error) {
            this.actionService.doAction({
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': error,
                    'type': 'warning',
                }
            });
            return null;
        }
    }
}
AddressAutofill.template = 'cyllo_map.AddressAutofill';

export const AddressAutofillField = {
    ...charField,
    component: AddressAutofill,
};
registry.category("fields").add("address_auto_fill", AddressAutofillField);