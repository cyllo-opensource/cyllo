/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

const { DateTime } = luxon;

const DATE_TABS = [
    { key: "today",    label: "Today",      days: 0 },
    { key: "tomorrow", label: "Tomorrow",   days: 1 },
    { key: "week",     label: "This Week",  days: 7 },
    { key: "all",      label: "Upcoming",   days: null },
];

export class BookingScreen extends Component {
    static template = "cyllo_appointment_restaurant.BookingScreen";
    static storeOnOrder = false;
    static props = {
        isShown: Boolean,
        selectedBookingId: { type: Number, optional: true },
        filterResourceId: { type: Number, optional: true },
    };

    setup() {
        this.pos   = usePos();
        this.orm   = useService("orm");
        this.ui    = useState(useService("ui"));
        this.popup = useService("popup");
        const initialBooking = this.props.selectedBookingId
            ? this.pos.appointments?.find((a) => a.id === this.props.selectedBookingId)
            : null;
        this.state = useState({
            selectedBooking: initialBooking ?? null,
            activeTab: "today",
        });
        this.tabs = DATE_TABS;
    }

    // ── data helpers ─────────────────────────────────────────────────────────

    _toTs(dt) {
        return dt?.ts ?? 0;
    }

    get bookings() {
        const all = this.pos.appointments ?? [];
        const now = DateTime.now();
        const todayStart   = now.startOf("day").ts;
        const tomorrowStart = now.startOf("day").plus({ days: 1 }).ts;
        const weekEnd      = now.startOf("day").plus({ days: 7 }).ts;

        return all
            .filter((a) => {
                if (this.props.filterResourceId && a.resource_id !== this.props.filterResourceId) return false;
                const ts = this._toTs(a.start_datetime);
                if (ts < todayStart) return false;
                if (["cancelled", "no_show", "done"].includes(a.state)) return false;
                switch (this.state.activeTab) {
                    case "today":    return ts < tomorrowStart;
                    case "tomorrow": return ts >= tomorrowStart && ts < now.startOf("day").plus({ days: 2 }).ts;
                    case "week":     return ts < weekEnd;
                    default:         return true;
                }
            })
            .sort((a, b) => this._toTs(a.start_datetime) - this._toTs(b.start_datetime));
    }

    getTabCount(tabKey) {
        const all = this.pos.appointments ?? [];
        const now = DateTime.now();
        const todayStart    = now.startOf("day").ts;
        const tomorrowStart = now.startOf("day").plus({ days: 1 }).ts;
        const weekEnd       = now.startOf("day").plus({ days: 7 }).ts;
        return all.filter((a) => {
            if (this.props.filterResourceId && a.resource_id !== this.props.filterResourceId) return false;
            const ts = this._toTs(a.start_datetime);
            if (ts < todayStart) return false;
            if (["cancelled", "no_show", "done"].includes(a.state)) return false;
            switch (tabKey) {
                case "today":    return ts < tomorrowStart;
                case "tomorrow": return ts >= tomorrowStart && ts < now.startOf("day").plus({ days: 2 }).ts;
                case "week":     return ts < weekEnd;
                default:         return true;
            }
        }).length;
    }

    getTableName(booking) {
        const resource = this.pos.getAppointmentResource(booking.resource_id);
        return resource?.name ?? _t("—");
    }

    getCustomerName(booking) {
        const partner = booking.partner_id
            ? this.pos.db.get_partner_by_id(booking.partner_id)
            : null;
        return partner?.name || booking.display_name || booking.name || _t("—");
    }

    getFormattedDateTime(dt) {
        if (!dt) return "—";
        const now = DateTime.now();
        if (dt.hasSame(now, "day")) return dt.toFormat("HH:mm");
        if (dt.hasSame(now.plus({ days: 1 }), "day")) return "Tomorrow " + dt.toFormat("HH:mm");
        return dt.toFormat("EEE d MMM, HH:mm");
    }

    getFormattedTime(dt) {
        if (!dt) return "—";
        return dt.toFormat("HH:mm");
    }

    getStatusLabel(state) {
        const map = {
            draft:      _t("Draft"),
            confirmed:  _t("Confirmed"),
            in_progress: _t("Checked In"),
            done:       _t("Done"),
            cancelled:  _t("Cancelled"),
            no_show:    _t("No Show"),
            rejected:   _t("Rejected"),
        };
        return map[state] ?? state;
    }

    getStatusClass(state) {
        const map = {
            draft:      "text-bg-warning",
            confirmed:  "text-bg-success",
            in_progress: "text-bg-primary",
            done:       "text-bg-secondary",
            cancelled:  "text-bg-danger",
            no_show:    "text-bg-danger",
            rejected:   "text-bg-danger",
        };
        return map[state] ?? "text-bg-secondary";
    }

    isSelected(booking) {
        return this.state.selectedBooking?.id === booking.id;
    }

    isPast(booking) {
        if (["draft","cancelled", "no_show", "done"].includes(booking.state)) return true;
        const dtNow = DateTime.now();
        const halfDuration = ((booking.duration || 1) / 2) * 3600000;
        const apptTs = this._toTs(booking.start_datetime);
        return apptTs <= dtNow.ts - halfDuration;
    }

    // ── event handlers ────────────────────────────────────────────────────────

    onSelectTab(tabKey) {
        this.state.activeTab = tabKey;
        this.state.selectedBooking = null;
    }

    onClickBooking(booking) {
        this.state.selectedBooking =
            this.state.selectedBooking?.id === booking.id ? null : booking;
    }

    onClickClose() {
        this.pos.closeScreen();
    }

    async onClickCheckIn(booking) {
        await this.orm.call(
            "appointment.appointment",
            "action_check_in",
            [[booking.id]],
        );
        booking.state = "in_progress";
    }

    async onClickCancel(booking) {
        await this.orm.write("appointment.appointment", [booking.id], {
            state: "cancelled",
        });
        booking.state = "cancelled";
        this.state.selectedBooking = null;
    }
}

registry.category("pos_screens").add("BookingScreen", BookingScreen);
