/** @odoo-module */
import PublicWidget from "@web/legacy/js/public/public_widget";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

export const OpenStreetMapWidget = PublicWidget.Widget.extend({
    selector: ".open_street_map_snippet",
    events: {
        'click .search_button_s': 'search',
        'click .refresh_button_s': 'RefreshSearch',
    },
    start() {
        this._super(...arguments);
        this.$placeNameInput = this.$('.place_name_input');
        this.$cityInput = this.$('.city_input');
        this.$pincodeInput = this.$('.pincode_input');
        this.$countryInput = this.$('.country_input');
        this.$latitudeInput = this.$('.latitude_input');
        this.$longitudeInput = this.$('.longitude_input');
        this.$stateInput = this.$('.state_input');
        const map = L.map('map').setView([51.505, -0.09], 5);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }).addTo(map);
        map.on('click', this.onMapClick.bind(this));
        this.map = map;
    },
    async search() {
        const self = this;
        const coordinates = await this.geocodeAddress();
        if (coordinates) {
            const latitude = coordinates['lat'];
            const longitude = coordinates['lon'];
            this.fetchAddressDetails(latitude, longitude)
            this.map.setView([latitude, longitude], 13);
            L.marker([latitude, longitude]).addTo(this.map);
        } else {
            self.call('dialog', 'add', ConfirmationDialog, { title: "No result", body: "Provide a valid information" });
        }
    },
    async geocodeAddress() {
        const url = 'https://nominatim.openstreetmap.org/search';
        const pay_load = {
            limit: 1,
            format: 'json',
            street: this.$placeNameInput.val() || '',
            postalcode: this.$pincodeInput.val() || '',
            city: '',
            state: '',
            country: this.$countryInput.val() || '',
        };

        try {
            const response = await fetch(`${url}?${new URLSearchParams(pay_load)}`);
            const data = await response.json();
            return data.length > 0 ? data[0] : null;
        } catch (error) {
            return null;
        }
    },
    onMapClick(e) {
        const {
            lat,
            lng
        } = e.latlng;
        this.fetchAddressDetails(lat, lng)
    },
    async fetchAddressDetails(latitude, longitude) {
        try {
            const url = `https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${latitude}&lon=${longitude}&zoom=18&addressdetails=1`;
            const response = await fetch(url);
            const data = await response.json();
            if(!this.$placeNameInput.val()){
                this.$placeNameInput.val(data.address['village'] || data.address['town'] || data.address['neighbourhood'] || data.address['road'] || data.address['name']);
            }
            this.$countryInput.val(data.address['country'] || '');
            this.$pincodeInput.val(data.address['postcode'] || '');
            this.$stateInput.val(data.address['state'] || '');
            this.$cityInput.val(data.address['city'] || '');
            this.$longitudeInput.val(longitude || '');
            this.$latitudeInput.val(latitude || '');
        } catch (error) {
        }
    },
    RefreshSearch() {
        this.$placeNameInput.val('');
        this.$countryInput.val('');
        this.$pincodeInput.val('');
        this.$stateInput.val('');
        this.$cityInput.val('');
        this.$longitudeInput.val('');
        this.$latitudeInput.val('');
    },
    destroy() {
        return this._super(...arguments);
    },
});

PublicWidget.registry.OpenStreetMapWidget = OpenStreetMapWidget;