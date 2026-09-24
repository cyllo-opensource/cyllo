/** @odoo-module **/
import { useService } from "@web/core/utils/hooks";
import { useRef, useState, Component, onMounted, onWillUpdateProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

export class StickyNoteItem extends Component {
    /**
    * @Extends Component
    */
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        this.notificationService = useService("notification");
        this.pallet = useRef("colorRef")
        this.titleRef = useRef("titleRef");
        this.descRef = useRef("descRef");
        this.state = useState({
            edit_color: this.props.colour || "rgb(253, 220, 180)",
            title: this.props.title,
        });
        onMounted(() => {
            if (this.props.is_edit) {
                this._highlightSelectedColor();
            }
        });
        onWillUpdateProps((nextProps) => {
            const wasEditing = this.props.is_edit;
            const nowEditing = nextProps.is_edit;
            if (wasEditing && !nowEditing) {
                this.state.title = nextProps.title;
                this.state.edit_color = nextProps.colour;
                if (this.titleRef?.el) this.titleRef.el.value = nextProps.title || '';
                if (this.descRef?.el) this.descRef.el.value = nextProps.description || '';
            }

            if (!wasEditing && nowEditing) {
                setTimeout(() => {
                    this._highlightSelectedColor();
                    this.state.title = nextProps.title;
                    this.state.edit_color = nextProps.colour;
                    if (this.titleRef?.el) this.titleRef.el.value = nextProps.title || '';
                    if (this.descRef?.el) this.descRef.el.value = nextProps.description || '';
                }, 0);
            }
        });

    }

    _highlightSelectedColor() {
        const el = this.pallet?.el;
        if (!el) return;
        const childrenArray = [...el.children];
        const currentColor = this.props.colour?.trim();
        childrenArray.forEach((item) => {
            const bgColor = item.style.backgroundColor?.trim();
            if (bgColor === currentColor) {
                item.classList.add("select");
            } else {
                item.classList.remove("select");
            }
        });
    }

    click_pallet(ev) {
        const childrenArray = [...this.pallet.el.children];
        childrenArray.forEach((item) => {
            if (item.contains(ev.target)) {
                item.classList.add('select');
            } else {
                item.classList.remove('select');
            }
        });
        const selected = childrenArray.find(item => item.classList.contains('select'));
        if (selected) {
            this.state.edit_color = selected.style.backgroundColor;
        }
    }

    async _remove(id) {
        // Removes a note by calling the ORM method unlink and triggers an event.
        await this.orm.call(
            "sticky.note",
            "unlink",
            [id],
        );
        this.env.bus.trigger("note_remove", id);
    }

    async _item_edit (id) {
        // make readonly false for editing note
        await this.env.bus.trigger("edit_button",{id});
    }

    async _cancel_edit(id) {
        // Trigger bus to clear edit mode
        this.env.bus.trigger("close_save");
    }

    async _item_save(id) {
        // edits a note by triggering an event with updated information.
        var today = new Date();
        var userTimeZoneOffset = today.getTimezoneOffset();
        var utcTime = today.getTime() + (userTimeZoneOffset * 60 * 1000);
        var userDateTime = new Date(utcTime);
        var userDate = today.getFullYear() + '-' + String(today.getMonth() + 1).padStart(2, '0') + '-' + String(today.getDate()).padStart(2, '0');
        var userTime = String(today.getHours()).padStart(2, '0') + ':' + String(today.getMinutes()).padStart(2, '0') + ':' + String(today.getSeconds()).padStart(2, '0');
        var userDateTimeFormatted = userDate + ' ' + userTime;

        const updatedTitle = this.titleRef.el.value;
        const updatedDescription = this.descRef.el.value;
        const updatedColor = this.state.edit_color;
        if (updatedTitle.trim() === '') {
            this.notificationService.add(
                _t("please add the title to save ..."), { type: "warning" });
            return;
        }
        if (updatedDescription.trim() === '') {
            this.notificationService.add(_t("please add the description to save ..."),
                { type: "warning" }
            );
            return;
        }
        var args = {
            title: updatedTitle,
            description: updatedDescription,
            colour: updatedColor,
            create_date: userDateTimeFormatted,
        }
        args['id'] = id
        await this.orm.call("sticky.note", "edit_note", [args]);
        this.env.bus.trigger("note_edit", args)
        this.env.bus.trigger("close_save")
    }
}
StickyNoteItem.template = "StickyNotesItem";