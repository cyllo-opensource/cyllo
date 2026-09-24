/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { FloorScreen } from "@pos_restaurant/app/floor_screen/floor_screen";
import { Table } from "@pos_restaurant/app/floor_screen/table";
import { useService } from "@web/core/utils/hooks";
// Import BookingScreen so it self-registers in the pos_screens registry.
import "@cyllo_appointment_restaurant/app/screens/booking_screen/booking_screen";

const { DateTime } = luxon;

const APPOINTMENT_RESOURCE_FIELDS = ["id", "name", "capacity", "pos_table_ids"];

patch(FloorScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
    },

    /**
     * `_save()` only writes back the table's geometry fields, so a freshly
     * created/duplicated table never carries its `appointment_resource_id`
     * locally even though the backend (`RestaurantTable.create()`) already
     * auto-created the linked resource. Fetch it once so the table shows
     * correctly straight away, without waiting for a full session reload.
     */
    async _createTableHelper(copyTable, duplicateFloor = false) {
        const table = await super._createTableHelper(...arguments);
        if (table && !table.appointment_resource_id) {
            const [resource] = await this.orm.searchRead(
                "appointment.resource",
                [["pos_table_ids", "in", table.id]],
                APPOINTMENT_RESOURCE_FIELDS,
                { limit: 1 }
            );
            if (resource) {
                table.appointment_resource_id = [resource.id, resource.name];
                this.pos.appointmentResources.push({
                    ...resource,
                    pos_table_ids: Array.isArray(resource.pos_table_ids)
                        ? resource.pos_table_ids
                        : [],
                });
            }
        }
        return table;
    },

    async duplicateTableOrFloor() {
        await super.duplicateTableOrFloor(...arguments);
        const tableIds = this.activeTables
            .filter((t) => !t.appointment_resource_id)
            .map((t) => t.id);
        if (!tableIds.length) {
            return;
        }
        const resources = await this.orm.searchRead(
            "appointment.resource",
            [["pos_table_ids", "in", tableIds]],
            APPOINTMENT_RESOURCE_FIELDS
        );
        for (const resource of resources) {
            const table = this.activeTables.find((t) =>
                resource.pos_table_ids.includes(t.id)
            );
            if (table) {
                table.appointment_resource_id = [resource.id, resource.name];
            }
            this.pos.appointmentResources.push({
                ...resource,
                pos_table_ids: Array.isArray(resource.pos_table_ids)
                    ? resource.pos_table_ids
                    : [],
            });
        }
    },
});

patch(Table.prototype, {
    // ── appointment helpers ─────────────────────────────────────────────────

    /**
     * Return ALL confirmed appointments for this table that fall within the
     * current display window (today, accounting for in-progress overlap),
     * sorted earliest-first.
     */
    getTableAppointments(table) {
        if (!table.appointment_resource_id) {
            return [];
        }
        const resourceId = Array.isArray(table.appointment_resource_id)
            ? table.appointment_resource_id[0]
            : table.appointment_resource_id;

        const allAppointments = this.pos.appointments ?? [];
        const appointments = allAppointments.filter((a) => a.resource_id === resourceId);
        if (!appointments.length) {
            return [];
        }

        const dtNow = DateTime.now();
        const tomorrowMidnight = dtNow.plus({ days: 1 }).startOf("day").ts;

        return appointments
            .filter((a) => {
                const halfDuration = ((a.duration || 1) / 2) * 3600000;
                const apptTs = a.start_datetime?.ts ?? 0;
                return (
                    apptTs > dtNow.ts - halfDuration &&
                    apptTs < tomorrowMidnight &&
                    !["cancelled", "no_show", "done"].includes(a.state)
                );
            })
            .sort((a, b) => (a.start_datetime?.ts ?? 0) - (b.start_datetime?.ts ?? 0));
    },

    /** Returns the earliest appointment for this table, or false. */
    getFirstAppointment(table) {
        const appts = this.getTableAppointments(table);
        return appts.length ? appts[0] : false;
    },

    /** Returns number of additional appointments beyond the first. */
    getExtraCount(table) {
        return Math.max(0, this.getTableAppointments(table).length - 1);
    },

    getFormattedDate(date) {
        return date.toFormat("HH:mm");
    },

    isCustomerLate(table) {
        const appt = this.getFirstAppointment(table);
        if (!appt) return false;
        return (
            DateTime.now() > appt.start_datetime &&
            ["confirmed", "in_progress"].includes(appt.state)
        );
    },

    /** Open the BookingScreen; it will show all bookings for this table. */
    onClickAppointment(ev, table) {
        if (!this.pos.isEditMode) {
            ev.stopPropagation();
            const appt = this.getFirstAppointment(table);
            if (appt) {
                this.pos.showScreen("BookingScreen", {
                    selectedBookingId: appt.id,
                    filterResourceId: Array.isArray(table.appointment_resource_id)
                        ? table.appointment_resource_id[0]
                        : table.appointment_resource_id,
                });
            }
        }
    },
});

