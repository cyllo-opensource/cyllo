/** @odoo-module **/
import { Component, useRef, useState, onMounted, onWillUpdateProps } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export class MapViewRenderer extends Component {
    setup() {
        this.state = useState({
            routeDirection: false,
            routeDistance: 0,
            routeDuration: 0
        });
        this.archInfo = this.props.archInfo
        this.model = this.props.list.resModel
        this.default_group = this.archInfo.defaultGroup ? true : false
        this.options = {}
        this.contacts = this.props.list.records
        this.uiService = useService("ui");
        this.archInfo = this.props.archInfo
        this.action = useService("action");
        this.orm = useService("orm");
        this.ref = useRef('root-renderer')
        this.actionService = useService("action")
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.RouteMap = useRef("route_map");
        this.ContactDetails = useRef("contact_details");
        this.searchInput = useRef("search_input_ref");
        this.placeNameInput = useRef("place_name_input");
        this.pincodeInput = useRef("pincode_input");
        this.warning_msg = useRef("warning_msg");
        this.countryInput = useRef("country_input");
        this.latitudeInput = useRef("latitude_input");
        this.longitudeInput = useRef("longitude_input");
        this.routeDuration = useRef("route_duration");
        this.routeDistance = useRef("route_distance");
        this.mapView = useRef("map_view");
        this.mapNotch = useRef("map_notch");
        this.drawnRoute = null;
        this.destinationChoose = false;
        onMounted(async () => {
            const map = L.map('map').setView([51.505, -0.09], 15);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            }).addTo(map);
            map.on('click', this.onMapClick.bind(this));
            this.map = map;
            const self = this;
            this.props.list.records.forEach(async (contact) => {
                L.marker([contact.data.partner_latitude, contact.data.partner_longitude]).addTo(self.map);
                this.map.setView([contact.data.partner_latitude, contact.data.partner_longitude], 1);
                self.props.list.load();
            });
        });
        onWillUpdateProps(newProps => {
            this.map.eachLayer(layer => {
                if (layer instanceof L.Marker) {
                    this.map.removeLayer(layer);
                }
            });
            newProps.list.records.forEach(async (contact) => {
                    L.marker([contact.data.partner_latitude, contact.data.partner_longitude]).addTo(this.map);
                    this.map.setView([contact.data.partner_latitude, contact.data.partner_longitude], 1);
            });
        });
    }

    FocusLocation(event, contact, temp) {
        if (event.button === 2) {
            event.preventDefault();
            var option = document.getElementById(("option_" + contact.id));
            if (option.classList.contains("d-none")) {
                option.classList.remove("d-none")
            } else {
                option.classList.add("d-none")
            }
        }
    }

    async getDirections(data) {
        const message = _t("Fetching Route...");
                                    this.warning_msg.el.classList.add("d-none")
        this.env.services.ui.block(message);
        const self = this;
        const current_company = await this.orm.searchRead(
            "res.company", [["id", "=", data._config.currentCompanyId]],
            ["name", "id", "street", "zip", "country_id",]);
        let current_company_address = await this.geocodeAddress(current_company[0].street, "", "");
        if (!current_company_address) {
          current_company_address = await this.geocodeAddress("", current_company[0].zip, "");
        }
        if (!current_company_address) {
            throw new Error('Please provide a valid company address');
        }
        const osrmUrl = `https://router.project-osrm.org/route/v1/driving/${current_company_address['lon']},${current_company_address['lat']};${data.data.partner_longitude},${data.data.partner_latitude}?steps=true&geometries=geojson`;
        L.marker([current_company_address['lat'], current_company_address['lon']], {
            icon: L.divIcon({
                className: 'custom-marker-start',
                html: '<div class="fa fa-bullseye"></div>',
            })
        }).addTo(this.map);
        L.marker([data.data.partner_latitude, data.data.partner_longitude], {
            icon: L.divIcon({
                className: 'custom-marker-end',
                html: '<div class="fa fa-bullseye"></div>',
            })
        }).addTo(this.map);
        L.marker([current_company_address['lat'], current_company_address['lon']]).addTo(self.map);
        try {
            const response = await fetch(encodeURI(osrmUrl));
            const nav = await response.json();
            if (nav.code === 'Ok') {
                const routes = nav.routes;
                self.state.routeDirection = nav;
                routes.forEach(async route => {
                const routeGeometry = route.geometry.coordinates;;
                this.state.routeDistance = (route.distance / 1000).toFixed(1);
                this.state.routeDuration = Math.ceil(route.duration / 60);
                this.drawRoute(routeGeometry);
                this.mapNotch.el.classList.remove('d-none')
                this.RouteMap.el.classList.remove('d-none')
                this.ContactDetails.el.classList.add('d-none')
                });
            } else {
                this.env.services.ui.unblock(message);
                this.warningDisplay()
            }
            this.env.services.ui.unblock();
        } catch (error) {
            this.env.services.ui.unblock();
            this.warningDisplay()
        }
    }

    focusLoc(contact) {
        this.map.setView([contact.data.partner_latitude, contact.data.partner_longitude], 16);
    }

    warningDisplay() {
        if (this.warning_msg.el.classList.contains("d-none")) {
            this.warning_msg.el.classList.remove("d-none")
        }
    }
    closeWarningDisplay() {
        this.warning_msg.el.classList.add("d-none")
    }

    drawRoute(routeGeometry) {
        const correctedRouteGeometry = routeGeometry.map(coord => [coord[1], coord[0]]);
        if (this.drawnRoute) {
            this.map.removeLayer(this.drawnRoute);
        }
        const polyline = L.polyline(correctedRouteGeometry, {
            color: 'blue'
        }).addTo(this.map);
        this.map.fitBounds(polyline.getBounds());
        this.drawnRoute = polyline;
    }

    closeNavigation() {
        window.location.reload();
    }

    async search() {
        const coordinates = await this.geocodeAddress(this.searchInput.el.value, "", "");
        if (coordinates) {
            const latitude = coordinates['lat'];
            const longitude = coordinates['lon'];
            this.fetchAddressDetails(latitude, longitude)
            this.map.setView([latitude, longitude], 13);
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

    async geocodeAddress(street, pincode, country_name) {
        const url = 'https://nominatim.openstreetmap.org/search';
        const pay_load = {
            limit: 1,
            format: 'json',
            street: street || '',
            postalcode: pincode || '',
            city: '',
            state: '',
            country: country_name || '',
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

    async geocodeAddressFetch(street, pincode, country_name) {
        const data = await this.orm.call('res.partner', 'get_location', ["", street, pincode, country_name]);
        return data
    }

    onMapClick(e) {
        const {
            lat,
            lng
        } = e.latlng;
        this.RefreshSearch()
        this.fetchAddressDetails(lat, lng)
    }

    async fetchAddressDetails(latitude, longitude) {
        try {
            const url = `https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${latitude}&lon=${longitude}&zoom=18&addressdetails=1`;
            const response = await fetch(url);
            const data = await response.json();
            this.placeNameInput.el.value = data.address['village'] || data.address['neighbourhood'] || data.address['city'] || data.address['town'] || '';
            this.countryInput.el.value = data.address['country'] || '';
            this.pincodeInput.el.value = data.address['postcode'] || '';
            this.longitudeInput.el.value = longitude || '';
            this.latitudeInput.el.value = latitude || '';
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

    RefreshSearch() {
        this.placeNameInput.el.value = '';
        this.countryInput.el.value = '';
        this.pincodeInput.el.value = '';
        this.longitudeInput.el.value = '';
        this.latitudeInput.el.value = '';
    }
}

MapViewRenderer.template = 'cyllo_map.MapViewRenderer';