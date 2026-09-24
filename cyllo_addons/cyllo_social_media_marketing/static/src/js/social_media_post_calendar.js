/** @odoo-module **/

import { CalendarCommonRenderer } from "@web/views/calendar/calendar_common/calendar_common_renderer";
import { CalendarCommonPopover } from "@web/views/calendar/calendar_common/calendar_common_popover";
import { CalendarController } from "@web/views/calendar/calendar_controller";
import { patch } from "@web/core/utils/patch";
import { renderToString } from "@web/core/utils/render";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { is24HourFormat } from "@web/core/l10n/dates";


function isPastCalendarClick(jsDate, isAllDay) {
    if (!jsDate) {
        return false;
    }
    if (isAllDay) {
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        const day = new Date(jsDate);
        day.setHours(0, 0, 0, 0);
        return day < today;
    }
    return jsDate < new Date();
}

patch(CalendarCommonRenderer.prototype, {
    setup() {
        super.setup();
        this.notification = useService("notification");
    },

    onDateClick(info) {
        if (
            this.props.model.resModel === "social.media.post" &&
            isPastCalendarClick(info.date, info.allDay)
        ) {
            this.notification.add(_t("You can't schedule a post in the past."), { type: "warning" });
            return;
        }
        super.onDateClick(...arguments);
    },

    async onSelect(info) {
        if (
            this.props.model.resModel === "social.media.post" &&
            isPastCalendarClick(info.start, info.allDay)
        ) {
            this.notification.add(_t("You can't schedule a post in the past."), { type: "warning" });
            this.fc.api.unselect();
            return;
        }
        await super.onSelect(...arguments);
    },

    convertRecordToEvent(record) {
        const event = super.convertRecordToEvent(record);
        if (this.props.model.resModel === "social.media.post") {
            const editable = record.rawRecord.state === "queue";
            event.editable = editable;
            event.startEditable = editable;
            event.durationEditable = editable;
        }
        return event;
    },

    onEventRender(info) {
        super.onEventRender(...arguments);
        if (this.props.model.resModel !== "social.media.post") {
            return;
        }
        const { el, event } = info;
        const record = this.props.model.records[event.id];
        if (!record) {
            return;
        }
        const template =
            this.props.model.scale === "month"
                ? "cyllo_social_media_marketing.CalendarEventCardCompact"
                : "cyllo_social_media_marketing.CalendarEventCard";
        const cardHtml = renderToString(template, {
            ...record,
            startTime: this.getStartTime(record),
            endTime: this.getEndTime(record),
        });
        const { children } = new DOMParser().parseFromString(cardHtml, "text/html").body;
        const existing = el.querySelector(".fc-content");
        if (existing) {
            existing.replaceWith(...children);
        }
    },
});

patch(CalendarCommonPopover.prototype, {
    computeDateTimeAndDuration() {
        super.computeDateTimeAndDuration();
        if (this.props.model.resModel !== "social.media.post") {
            return;
        }
        const record = this.props.record;
        if (!record.isTimeHidden && !record.isAllDay) {
            const timeFormat = is24HourFormat() ? "HH:mm" : "hh:mm a";
            this.time = record.start.toFormat(timeFormat);
        }
        this.timeDuration = null;
    },
});

patch(CalendarController.prototype, {
    get editRecordDefaultDisplayText() {
        if (this.model.resModel === "social.media.post") {
            return _t("New Post");
        }
        return super.editRecordDefaultDisplayText;
    },
});
