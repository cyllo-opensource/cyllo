/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { Navbar } from "@point_of_sale/app/navbar/navbar";
import { BookingScreen } from "@cyllo_appointment_restaurant/app/screens/booking_screen/booking_screen";
import { deserializeDateTime } from "@web/core/l10n/dates";

const { DateTime } = luxon;

/**
 * Normalize a raw `appointment.appointment` dict - as returned either by
 * `search_read` (on initial session load) or by the TABLE_BOOKING bus
 * message (on real-time create/write) - into the shape consumed by the
 * floor screen and booking screen:
 *   - Datetime fields are parsed into Luxon DateTime instances.
 *   - Many2one fields are normalized to a plain id (search_read returns
 *     [id, display_name] tuples, the bus payload already sends plain ids).
 */
function parseAppointment(raw) {
    return {
        ...raw,
        start_datetime: raw.start_datetime ? deserializeDateTime(raw.start_datetime) : false,
        end_datetime: raw.end_datetime ? deserializeDateTime(raw.end_datetime) : false,
        resource_id: Array.isArray(raw.resource_id) ? raw.resource_id[0] : raw.resource_id,
        partner_id: Array.isArray(raw.partner_id) ? raw.partner_id[0] : raw.partner_id || false,
    };
}

patch(PosStore.prototype, {
    /**
     * PosStore funnels every model loaded via
     * `_pos_ui_models_to_load` through this single hook once, right after
     * the initial RPC fetch. This is the v17 equivalent of what later
     * versions do automatically through the relational data-model registry.
     */
    async _processData(loadedData) {
        await super._processData(...arguments);
        this.appointmentResources = (loadedData["appointment.resource"] || []).map((r) => ({
            ...r,
            pos_table_ids: Array.isArray(r.pos_table_ids) ? r.pos_table_ids : [],
        }));
        this.appointments = (loadedData["appointment.appointment"] || []).map(parseAppointment);
    },

    /**
     * Listen for TABLE_BOOKING bus messages pushed by the server
     * (appointment.appointment create/write/unlink) and update the local
     * appointment data in the POS store accordingly.
     */
    async setup() {
        await super.setup(...arguments);
        const busService = this.env.services.bus_service;
        busService.addEventListener("notification", ({ detail: notifications }) => {
            for (const { type, payload } of notifications) {
                if (type !== "TABLE_BOOKING") {
                    continue;
                }
                const { command, event } = payload;
                if (!event) {
                    continue;
                }
                if (command === "ADDED") {
                    const appt = parseAppointment(event);
                    const idx = this.appointments.findIndex((a) => a.id === appt.id);
                    if (idx !== -1) {
                        this.appointments[idx] = appt;
                    } else {
                        this.appointments.push(appt);
                    }
                } else if (command === "REMOVED") {
                    const idx = this.appointments.findIndex((a) => a.id === event.id);
                    if (idx !== -1) {
                        this.appointments.splice(idx, 1);
                    }
                }
            }
        });
    },

    /** Mirrors the lookup that `appointment.resource` model.get(id) used to do. */
    getAppointmentResource(id) {
        return this.appointmentResources?.find((r) => r.id === id);
    },

    /**
     * Open the booking screen with a specific booking pre-selected
     * (used when tapping the appointment badge on a floor table).
     */
    editBooking(appt) {
        this.showScreen("BookingScreen", { selectedBookingId: appt.id });
    },

    /**
     * Open the booking screen directly.
     */
    showBookingScreen() {
        this.showScreen("BookingScreen");
    },
});

/**
 * Patch the Navbar to add a "Bookings" entry in the hamburger menu.
 */
patch(Navbar.prototype, {
    /**
     * Count of today's active bookings - used for the badge in the menu.
     * Optional-chained so it never crashes before the POS store or
     * appointment data is available.
     */
    get todayBookingCount() {
        const allAppointments = this.pos?.appointments ?? [];
        if (!allAppointments.length) {
            return 0;
        }
        const dtNow = DateTime.now();
        const todayStart = dtNow.startOf("day").ts;
        const tomorrowStart = dtNow.plus({ days: 1 }).startOf("day").ts;
        return allAppointments.filter((a) => {
            const ts = a.start_datetime?.ts ?? 0;
            return (
                ts >= todayStart &&
                ts < tomorrowStart &&
                !["cancelled", "no_show", "done"].includes(a.state)
            );
        }).length;
    },

    /**
     * Called when the Bookings hamburger item is clicked.
     */
    onBookingsButtonClick() {
        this.state.isMenuOpened = false;
        if (this.pos.mainScreen.component === BookingScreen) {
            this.pos.closeScreen();
        } else {
            this.pos.showScreen("BookingScreen");
        }
    },
});
