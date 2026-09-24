/** @odoo-module **/
import { registry } from "@web/core/registry";
import { CharField, charField} from '@web/views/fields/char/char_field';
import { _t } from "@web/core/l10n/translation";
import { Component, useRef } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
export class AddressFromMap extends CharField {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.AddressInput = useRef("input");
        this.placeNameInput = useRef("place_name_input");
        this.modalContainerMap = useRef("open_street_map");
        this.cityInput = useRef("city_input");
        this.pincodeInput = useRef("pincode_input");
        this.countryInput = useRef("country_input");
        this.latitudeInput = useRef("latitude_input");
        this.longitudeInput = useRef("longitude_input");
        this.stateInput = useRef("state_input");
        this.SearchInput = useRef("search_input_ref");
    }
    async SearchOnMap() {
        const coordinates = await this.geocodeAddress();
        if (coordinates) {
            const latitude = coordinates['lat'];
            const longitude = coordinates['lon'];
            this.map.setView([latitude, longitude], 13);
        } else {
            this.actionService.doAction({
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': 'No place found',
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
            street: this.SearchInput.el.value || '',
            postalcode: '',
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
                    'message': 'Failed to fetch place, try after some time',
                    'type': 'warning',
                }
            });
            return null;
        }
    }
    async OpenMap() {
        this.modalContainerMap.el.classList.remove("d-none");
        let map = L.map('map').setView([40.737, -73.923], 15);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }).addTo(map);
        map.on('click', this.onMapClick.bind(this));
        this.map = map;
    }
    CloseMap() {
        this.modalContainerMap.el.classList.add("d-none");
        if (this.map) {
            this.map.remove();
            this.map = null;
        }
    }
    onMapClick(e) {
        const { lat, lng } = e.latlng;
        this.fetchAddressDetails(lat, lng)
    }
    async fetchAddressDetails(latitude, longitude) {
        try {
            const url = `https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${latitude}&lon=${longitude}&zoom=18&addressdetails=1`;
            const response = await fetch(url);
            const data = await response.json();
            this.placeNameInput.el.value = data.address['village'] || data.address['town'] || data.address['neighbourhood'] || data.address['road'] || '';
            this.countryInput.el.value = data.address['country'] || '';
            this.pincodeInput.el.value = data.address['postcode'] || '';
            this.stateInput.el.value = data.address['state'] || '';
            this.cityInput.el.value = data.address['city'] || '';
            this.longitudeInput.el.value = longitude || '';
            this.latitudeInput.el.value = latitude || '';
        } catch (error) {
            this.actionService.doAction({
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': 'Failed to fetch place ,try after some time',
                    'type': 'warning',
                }
            });
        }
    }
    async SaveAddress() {
        this.modalContainerMap.el.classList.add("d-none");
        if (this.map) {
            this.map.remove();
            this.map = null;
            const country = await this.orm.searchRead("res.country", [
                ['name', '=', this.countryInput.el.value]
            ], ['name', 'id']);
            const state = await this.orm.searchRead("res.country.state", [
                ['name', '=', this.stateInput.el.value]
            ], ['name', 'id']);
            if (this.props.record.resModel == 'hr.employee') {
                this.props.record.data.private_street = this.placeNameInput.el.value
                this.props.record.data.private_zip = this.pincodeInput.el.value
                this.props.record.data.private_city = this.cityInput.el.value
                this.props.record._changes.private_street = this.placeNameInput.el.value
                this.props.record._changes.private_zip = this.pincodeInput.el.value
                this.props.record._changes.private_city = this.cityInput.el.value
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
                this.props.record.data.street = this.placeNameInput.el.value
                this.props.record.data.zip = this.pincodeInput.el.value
                this.props.record.data.city = this.cityInput.el.value
                this.props.record._changes.street = this.placeNameInput.el.value
                this.props.record._changes.zip = this.pincodeInput.el.value
                this.props.record._changes.city = this.cityInput.el.value
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
        }
    }
}
AddressFromMap.template = 'cyllo_map.AddressFromMap';

export const AddressFromMapField = {
    ...charField,
    component: AddressFromMap,
};
registry.category("fields").add("address_from_map", AddressFromMapField);