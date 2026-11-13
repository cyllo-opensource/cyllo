/** @odoo-module **/
import { Component, markup, onWillStart, onMounted, useRef, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

/**
 * Write or edit the note attached to a sheet.
 *
 * The editor is a contenteditable with a three-button toolbar rather than
 * the framework's rich editor. HtmlField wants a form-view record to read
 * and write and there is none here - the dashboard holds plain sheet dicts -
 * and this version's Wysiwyg is a legacy widget that an OWL dialog can only
 * reach through an adapter. A note is a paragraph or two of commentary, so
 * bold, italic and a bullet list is the whole of what it needs, and the HTML
 * it stores is the same HTML the other version reads.
 */
export class NoteDialog extends Component {
    static template = "cyllo_analytics.NoteDialog";
    static components = { Dialog };
    static props = {
        sheetId: Number,
        // The dashboard and the filters in force are what make a note the
        // right note: the same chart carries different commentary on another
        // dashboard, or through another period.
        configId: Number,
        filters: { type: Object, optional: true },
        sheetName: { type: String, optional: true },
        onSaved: { type: Function, optional: true },
        close: Function,
    };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({
            saving: false, loaded: false, savedOn: false,
            // Every note on this chart, and whether the reader has asked to
            // see them. Loaded up front rather than on the click: the link
            // only earns its place when there is something behind it, and
            // that cannot be known without asking.
            history: [], showHistory: false,
        });
        // Held outside state: it changes on every keystroke and nothing
        // re-renders on it, so making it reactive would only cost renders.
        this.editorRef = useRef("editor");
        this.note = "";
        // Loaded here rather than passed in: the caller knows which chart is
        // open, but only the server knows what was written for this exact
        // combination of dashboard and filters.
        onWillStart(async () => {
            const found = await this.orm.call(
                "dashboard.sheet.note", "note_for",
                [this.props.sheetId, this.props.configId, this.props.filters || {}]);
            this.note = found.note_html || "";
            this.state.savedOn = found.saved_on || false;
            this.state.history = await this.loadHistory();
            this.state.loaded = true;
        });
        // Seeded after the element exists, and through innerHTML: the note
        // arrives over RPC as a plain string, so writing it as text would
        // show its own tags. Safe because note_html is sanitize=True.
        onMounted(() => {
            if (this.editorRef.el) {
                this.editorRef.el.innerHTML = this.note || "";
            }
        });
    }

    /**
     * Every note written against this chart, newest first.
     *
     * Failure is swallowed on purpose. This is a convenience beside the
     * editor, and losing it must never stop somebody writing the note they
     * came here to write.
     */
    async loadHistory() {
        try {
            const history = await this.orm.call(
                "dashboard.sheet.note", "notes_history",
                [this.props.sheetId, this.props.configId, this.props.filters || {}]);
            // Marked up here rather than in the template: note_html arrives
            // over RPC as a plain string, and t-out would print its tags.
            // Safe because the field is sanitize=True.
            return (history || []).map((entry) => ({
                ...entry, markup: markup(entry.note_html || ""),
            }));
        } catch {
            return [];
        }
    }

    toggleHistory() {
        this.state.showHistory = !this.state.showHistory;
    }

    /** The filters this note belongs to, as something a person can read. */
    get filterSummary() {
        const filters = this.props.filters || {};
        const parts = Object.keys(filters)
            .filter((code) => filters[code])
            .sort()
            .map((code) => `${code}: ${filters[code]}`);
        return parts.length ? parts.join(" · ") : _t("no filters applied");
    }

    /**
     * Apply a formatting command to the selection.
     *
     * execCommand is deprecated and still the only thing every browser
     * implements for a contenteditable. The alternative is a selection and
     * range implementation of bold - which is a text editor, and not what
     * this dialog is. Focus is restored first because clicking the button
     * took it away, and a command with no selection does nothing.
     */
    format(command) {
        this.editorRef.el?.focus();
        document.execCommand(command, false, null);
    }

    async onSave() {
        if (this.state.saving) {
            return;
        }
        this.state.saving = true;
        try {
            const content = this.editorRef.el ? this.editorRef.el.innerHTML : "";
            // Stored against this sheet, this dashboard and these filters. The
            // server decides whether the markup counts as content and deletes
            // the row when it does not, so emptiness is judged in one place
            // rather than differently here and there.
            const saved = await this.orm.call(
                "dashboard.sheet.note", "save_note",
                [this.props.sheetId, this.props.configId,
                 this.props.filters || {}, content]);
            this.props.onSaved?.(saved.note_html || false, saved);
            this.props.close();
        } catch (error) {
            this.state.saving = false;
            this.notification.add(
                _t("The note could not be saved."), { type: "danger" });
            throw error;
        }
    }
}
