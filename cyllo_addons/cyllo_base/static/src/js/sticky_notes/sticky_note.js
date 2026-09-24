/** @odoo-module **/
import { useService, useBus } from "@web/core/utils/hooks";
import { Component, useExternalListener, useState, onWillStart, useRef } from "@odoo/owl";
import { StickyNoteAdd } from "./sticky_notes_add";
import { StickyNoteCreate } from "./sticky_notes_create";
import { StickyNoteItem } from "./sticky_notes_item";
import { StickyNoteUpdate } from "./sticky_notes_update";
import { session } from "@web/session";
import {_t} from "@web/core/l10n/translation";
export class StickyNotes extends Component {
    /**
    * @extends Component
    */
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        this.notificationService = useService("notification");
        this.action = useService("action");
        this.pallet = useRef("colorRef")
        this.state = useState({
            isEdit: false,
            notes: [],
            edit_note_id: null,
        })
        this.menuRef = useRef("menuRef")
        useExternalListener(document, "keydown", this.onKeyDown);
        useExternalListener(window, "click", this.onWindowClick);
        useBus(this.env.bus, 'note_updates', ({detail})  => {
            this.state.notes.unshift(detail)
            this.state.isEdit = !this.state.isEdit
        });
        useBus(this.env.bus, 'note_remove', ({detail})  => {
            const indexToRemove = this.state.notes.findIndex(note => note.id === detail);
            /**
            * Check if a note with a specific ID exists in the 'notes'
            array and remove it if found.
            */
            if (indexToRemove !== -1) {
                this.state.notes.splice(indexToRemove, 1);
            }
        });
        useBus(this.env.bus, 'edit_button', ({detail})  => {
            if (this.state.isEdit) {
                this.notificationService.add(
                _t("Cancel the creating note to continue..."), { type: "warning" });
                return;
            }
            else{
                this.state.edit_note_id = detail.id;
            }
        });
        useBus(this.env.bus, 'close_save', ()  => {
            this.state.edit_note_id = null;
        });
        useBus(this.env.bus, 'note_edit', ({ detail }) => {
            const noteIndex = this.state.notes.findIndex((note) => note.id === detail.id);
            /**
            * Update or add a note to the 'notes' array based on the 'detail.id'.
            */
            if (noteIndex !== -1) {
                this.state.notes[noteIndex] = detail;
            } else {
                this.state.notes.push(detail);
            }
            this.state.isEdit = false
        });
        var self = this;
        var current_user = session.uid;
        onWillStart(async () => {
            // It performs a search operation in 'sticky.note' model using the ORM to retrieve notes
            await this.orm.call(
                "sticky.note",
                "search_read",
                [[['create_uid', '=', current_user]]],
                { order : 'id desc'}
            ).then(function(result  ) {
                self.state.notes = result;
            });
        });
    }

    async _close_note() {
        // Closes the note by triggering an event on the bus.
        this.env.noteClose()
    }

    onWindowClick(ev) {
        if (!$(this.menuRef.el).is(ev.target) && $(this.menuRef.el).has(ev.target).length === 0 && !this.state.isEdit == true) {
            this._close_note();
        }
    }

    onKeyDown(ev) {
        if (ev.key === 'Escape' && !this.state.isEdit == true) {
            this._close_note()
        }
    }
}
StickyNotes.template = "StickyNotes";
StickyNotes.components = { StickyNoteAdd, StickyNoteCreate, StickyNoteItem, StickyNoteUpdate};