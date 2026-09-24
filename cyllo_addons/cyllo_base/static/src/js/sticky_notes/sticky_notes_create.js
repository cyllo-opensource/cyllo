/** @odoo-module **/
import { useService } from "@web/core/utils/hooks";
import { Component, onMounted, useState, onWillUpdateProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
const { useRef } = owl;
export class StickyNoteCreate extends Component {
    /**
     * @extends Component
    */
    setup() {
        this.orm = useService("orm");
        this.notificationService = useService("notification");
        this.title = useRef("noteTitle")
        this.description = useRef("noteDescription")
        this.pallet = useRef("colorRef")
        this.state = useState({
            note_color : "rgb(253, 220, 180)"
        });
        super.setup(...arguments);
        /**
        * Function executed when the component is mounted.
        */
        onMounted(() => {
            this.title.el.value = this.props.title || '';
            this.description.el.value = this.props.description || '';
            this.pallet.el.value = this.props.colour ||'';
            this.state.note_color = this.props.colour || this.state.note_color;

            const childrenArray = [...this.pallet.el.children];
            childrenArray.forEach((item) => {
                if (item.style.backgroundColor === this.state.note_color) {
                    item.classList.add('select');
                } else {
                    item.classList.remove('select');
                }
            });
        });

        onWillUpdateProps(async (nextProps) => {
            this.title.el.value = nextProps.title || '';
            this.description.el.value = nextProps.description || '';
            this.pallet.el.value = nextProps.colour ||'';
            this.state.note_color = nextProps.colour || this.state.note_color;
            const childrenArray = [...this.pallet.el.children];
            childrenArray.forEach((item) => {
                if (item.style.backgroundColor === this.state.note_color) {
                    item.classList.add('select');
                } else {
                    item.classList.remove('select');
                }
            });
        });
    }

    click_pallet(ev) {
        // Handles click events on a pallet element and adds or removes the 'select' class for choosing the color
        const childrenArray = [...this.pallet.el.children];
        childrenArray.forEach((item) => {
            if (item.contains(ev.target)) {
                item.classList.add('select');
            }
            if (!item.contains(ev.target)) {
                item.classList.remove('select');
            }
        });
        const selectedColorElement = childrenArray.find(item => item.classList.contains('select'));
        this.state.note_color = String(selectedColorElement.style.backgroundColor);
    }

    async _note_save (ev) {
        // saves a note with the provided title and description.
        // Assuming today is defined as a Date object
        var today = new Date();
        var userTimeZoneOffset = today.getTimezoneOffset();
        var utcTime = today.getTime() + (userTimeZoneOffset * 60 * 1000);
        var userDateTime = new Date(utcTime);
        var userDate = today.getFullYear() + '-' + String(today.getMonth() + 1).padStart(2, '0') + '-' + String(today.getDate()).padStart(2, '0');
        var userTime = String(today.getHours()).padStart(2, '0') + ':' + String(today.getMinutes()).padStart(2, '0') + ':' + String(today.getSeconds()).padStart(2, '0');
        var userDateTimeFormatted = userDate + ' ' + userTime;
        const title = this.title.el.value;
        const description = this.description.el.value;
        if (title.trim() === '') {
            this.notificationService.add(
            _t("please add the title to save ..."), { type: "warning" });
            return;
        }
        if (description.trim() === '') {
            this.notificationService.add(_t("please add the description to save ..."),
                { type: "warning" }
            );
            return;
        }
        var args = {
            title: title,
            description: description,
            colour: this.state.note_color,
            create_date : userDateTimeFormatted,
        }
        var datas = await this.orm.call("sticky.note","create",[args],);
        args['id'] = datas
        this.env.bus.trigger("note_updates", args);
    }

    async _note_cancel(ev){
        $('.o_button_close').click()
    }

    onKeydown(ev) {
        // Handles the 'keydown' event and triggers a function for saving the note
        if (ev.key === 'Enter') {
            this._note_save();
        }
    }
}
StickyNoteCreate.template = "StickyNotesCreate";