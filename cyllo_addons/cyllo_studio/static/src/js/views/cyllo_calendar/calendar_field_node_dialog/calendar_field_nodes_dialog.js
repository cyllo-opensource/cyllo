/** @odoo-module **/

/**
 * CalendarViewDialog
 *
 * Extends CalendarCommonPopover to provide a fully interactive calendar popover
 * for Odoo Studio with support for:
 *  - Adding, editing, and deleting calendar fields
 *  - Assigning widgets, icons, and attributes to fields
 *  - Drag-and-drop reordering of calendar items
 *  - Undo/Redo of changes using sessionStorage
 *  - Popovers for editing field properties
 *
 * Props:
 *  - showInvisible: function to toggle invisible fields
 *  - invisible: boolean to indicate visibility
 *  - close: function to close the dialog
 *  - record: optional object for pre-selected record
 *  - model: object containing model metadata and fields
 *  - viewId: numeric ID of the current calendar view
 */
import {onMounted, useState, useRef, onError} from "@odoo/owl";
import {useService, useOwnedDialogs} from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { Dropdown } from "@web/core/dropdown/dropdown";
import {DropdownItem} from "@web/core/dropdown/dropdown_item";
import {MultiRecordSelector} from "@web/core/record_selectors/multi_record_selector";
import {MultiSelectDropDown} from "@cyllo_studio/js/view_editor/dropdown/multi_select_dropdown/multi_select_dropdown";
import { ExpressionEditorDialog } from "@web/core/expression_editor_dialog/expression_editor_dialog";
import { sortBy } from "@web/core/utils/arrays";
import { Record } from "@web/model/record";
import { Field } from "@web/views/fields/field";
import { CalendarCommonPopover } from "@web/views/calendar/calendar_common/calendar_common_popover";
import {CalendarDialogBox} from "@cyllo_studio/js/views/cyllo_calendar/calendar_dialog/calendar_dialog_box";
const ICONCLASS = ["fa-500px","fa-address-book","fa-address-book-o","fa-address-card","fa-address-card-o","fa-adjust","fa-adn","fa-align-center","fa-align-justify","fa-align-left","fa-align-right","fa-amazon","fa-ambulance","fa-american-sign-language-interpreting","fa-anchor","fa-android","fa-angellist","fa-angle-double-down","fa-angle-double-left","fa-angle-double-right","fa-angle-double-up","fa-angle-down","fa-angle-left","fa-angle-right","fa-angle-up","fa-apple","fa-archive","fa-area-chart","fa-arrow-circle-down","fa-arrow-circle-left","fa-arrow-circle-o-down","fa-arrow-circle-o-left","fa-arrow-circle-o-right","fa-arrow-circle-o-up","fa-arrow-circle-right","fa-arrow-circle-up","fa-arrow-down","fa-arrow-left","fa-arrow-right","fa-arrow-up","fa-arrows","fa-arrows-alt","fa-arrows-h","fa-arrows-v","fa-asl-interpreting","fa-assistive-listening-systems","fa-asterisk","fa-at","fa-audio-description","fa-automobile","fa-backward","fa-balance-scale","fa-ban","fa-bandcamp","fa-bank","fa-bar-chart","fa-bar-chart-o","fa-barcode","fa-bars","fa-bath","fa-bathtub","fa-battery","fa-battery-0","fa-battery-1","fa-battery-2","fa-battery-3","fa-battery-4","fa-battery-empty","fa-battery-full","fa-battery-half","fa-battery-quarter","fa-battery-three-quarters","fa-bed","fa-beer","fa-behance","fa-behance-square","fa-bell","fa-bell-o","fa-bell-slash","fa-bell-slash-o","fa-bicycle","fa-binoculars","fa-birthday-cake","fa-bitbucket","fa-bitbucket-square","fa-bitcoin","fa-black-tie","fa-blind","fa-bluetooth","fa-bluetooth-b","fa-bold","fa-bolt","fa-bomb","fa-book","fa-bookmark","fa-bookmark-o","fa-braille","fa-briefcase","fa-btc","fa-bug","fa-building","fa-building-o","fa-bullhorn","fa-bullseye","fa-bus","fa-buysellads","fa-cab","fa-calculator","fa-calendar","fa-calendar-check-o","fa-calendar-minus-o","fa-calendar-o","fa-calendar-plus-o","fa-calendar-times-o","fa-camera","fa-camera-retro","fa-car","fa-caret-down","fa-caret-left","fa-caret-right","fa-caret-square-o-down","fa-caret-square-o-left","fa-caret-square-o-right","fa-caret-square-o-up","fa-caret-up","fa-cart-arrow-down","fa-cart-plus","fa-cc","fa-cc-amex","fa-cc-diners-club","fa-cc-discover","fa-cc-jcb","fa-cc-mastercard","fa-cc-paypal","fa-cc-stripe","fa-cc-visa","fa-certificate","fa-chain","fa-chain-broken","fa-check","fa-check-circle","fa-check-circle-o","fa-check-square","fa-check-square-o","fa-chevron-circle-down","fa-chevron-circle-left","fa-chevron-circle-right","fa-chevron-circle-up","fa-chevron-down","fa-chevron-left","fa-chevron-right","fa-chevron-up","fa-child","fa-chrome","fa-circle","fa-circle-o","fa-circle-o-notch","fa-circle-thin","fa-clipboard","fa-clock-o","fa-clone","fa-close","fa-cloud","fa-cloud-download","fa-cloud-upload","fa-cny","fa-code","fa-code-fork","fa-codepen","fa-codiepie","fa-coffee","fa-cog","fa-cogs","fa-columns","fa-comment","fa-comment-o","fa-commenting","fa-commenting-o","fa-comments","fa-comments-o","fa-compass","fa-compress","fa-connectdevelop","fa-contao","fa-copy","fa-copyright","fa-creative-commons","fa-credit-card","fa-credit-card-alt","fa-crop","fa-crosshairs","fa-css3","fa-cube","fa-cubes","fa-cut","fa-cutlery","fa-dashboard","fa-dashcube","fa-database","fa-deaf","fa-deafness","fa-dedent","fa-delicious","fa-desktop","fa-deviantart","fa-diamond","fa-digg","fa-dollar","fa-dot-circle-o","fa-download","fa-dribbble","fa-drivers-license","fa-drivers-license-o","fa-dropbox","fa-drupal","fa-edge","fa-edit","fa-eercast","fa-eject","fa-ellipsis-h","fa-ellipsis-v","fa-empire","fa-envelope","fa-envelope-o","fa-envelope-open","fa-envelope-open-o","fa-envelope-square","fa-envira","fa-eraser","fa-etsy","fa-eur","fa-euro","fa-exchange","fa-exclamation","fa-exclamation-circle","fa-exclamation-triangle","fa-expand","fa-expeditedssl","fa-external-link","fa-external-link-square","fa-eye","fa-eye-slash","fa-eyedropper","fa-fa","fa-facebook","fa-facebook-f","fa-facebook-official","fa-facebook-square","fa-fast-backward","fa-fast-forward","fa-fax","fa-feed","fa-female","fa-fighter-jet","fa-file","fa-file-archive-o","fa-file-audio-o","fa-file-code-o","fa-file-excel-o","fa-file-image-o","fa-file-movie-o","fa-file-o","fa-file-pdf-o","fa-file-photo-o","fa-file-picture-o","fa-file-powerpoint-o","fa-file-sound-o","fa-file-text","fa-file-text-o","fa-file-video-o","fa-file-word-o","fa-file-zip-o","fa-files-o","fa-film","fa-filter","fa-fire","fa-fire-extinguisher","fa-firefox","fa-first-order","fa-flag","fa-flag-checkered","fa-flag-o","fa-flash","fa-flask","fa-flickr","fa-floppy-o","fa-folder","fa-folder-o","fa-folder-open","fa-folder-open-o","fa-font","fa-font-awesome","fa-fonticons","fa-fort-awesome","fa-forumbee","fa-forward","fa-foursquare","fa-free-code-camp","fa-frown-o","fa-futbol-o","fa-gamepad","fa-gavel","fa-gbp","fa-ge","fa-gear","fa-gears","fa-genderless","fa-get-pocket","fa-gg","fa-gg-circle","fa-gift","fa-git","fa-git-square","fa-github","fa-github-alt","fa-github-square","fa-gitlab","fa-gittip","fa-glass","fa-glide","fa-glide-g","fa-globe","fa-google","fa-google-plus","fa-google-plus-circle","fa-google-plus-official","fa-google-plus-square","fa-google-wallet","fa-graduation-cap","fa-gratipay","fa-grav","fa-group","fa-h-square","fa-hacker-news","fa-hand-grab-o","fa-hand-lizard-o","fa-hand-o"]
import { CylloStudioDropdown } from "@cyllo_studio/js/view_editor/dropdown/CylloStudioDropdown";
import {_t} from "@web/core/l10n/translation";

export class CalendarViewDialog extends CalendarCommonPopover {
    static template = "cyllo_studio.CalendarViewDialog";
    static props = {
        showInvisible: Function,
        invisible: Boolean,
        close: Function,
        record:{
			type: Object,
			optional: true
		},
        model: Object,
        viewId: Number,
    }
    static components = {
        ...CalendarCommonPopover.components,
        CalendarDialogBox,
        MultiRecordSelector,
        MultiSelectDropDown,
        Record,
        Field,
        Dropdown,
        DropdownItem,
        CylloStudioDropdown
    };
    setup() {
        this.time = null;
        this.timeDuration = null;
        this.date = null;
        this.dateDuration = null;
        if (this.props.record.id) {
            this.computeDateTimeAndDuration();
        }
        onError((err) => this.undoAction(err))
        this.rpc = useService("rpc");
        this.orm = useService("orm");
        this.action = useService("action");
        this.fieldNodeRef = useRef('fieldNodeRef')
        this.addDialog = useOwnedDialogs();
        this.notification = useService('effect')
        this.state = useState({
            editable: false,
            item: {},
            iconToggle: false,
            avatarFields: [],
            showInvisible: this.props.invisible,
            widgetSelect: '',
            dateField :false,
        })
        /**
         * Initialize drag-and-drop for calendar items
         *
         * Uses SortableJS to enable dragging fields in the calendar popover.
         * Stores changes in sessionStorage for undo/redo.
         * Integrates with autoScroll for smoother dragging experience.
         */
        onMounted(() => {
    const self = this;
    if (!this.fieldNodeRef.el) {
        return;
    }

    const container = this.fieldNodeRef.el;

    // Destroy existing sortable if any
    const existingSortable = Sortable.get(container);
    if (existingSortable) existingSortable.destroy();

    const sortable = Sortable.create(container, {
        animation: 150,
        ghostClass: 'sortable-ghost',

        // Only allow dragging via the handle
        handle: '.handle-drag',

        onEnd: async function(evt) {
            const el = evt.item;
            let path = el.getAttribute("cy-xpath");

            // Get sibling after the dropped element
            const sibling = el.nextElementSibling || null;
            const nextSiblingPath = sibling?.getAttribute("cy-xpath") || null;
            const sibling_path = nextSiblingPath || el.previousElementSibling.getAttribute("cy-xpath");
            const position = nextSiblingPath ? "before" : "after";

            self.env.services.ui.block();
            try {
                const response = await self.rpc("cyllo_studio/calendar/move/item", {
                    view_id: self.props.viewId,
                    model: self.props.model.resModel,
                    path,
                    position,
                    sibling_path,
                });
                if (response) {
                    let storedArray = JSON.parse(sessionStorage.getItem('UndoRedo')) || [];
                    let cleanedStr = response.replace(/\s+/g, ' ').trim();
                    storedArray.push(cleanedStr);
                    sessionStorage.setItem('UndoRedo', JSON.stringify(storedArray));
                    sessionStorage.setItem('ReDO', JSON.stringify([]));
                }
            } finally {
                self.env.services.ui.unblock();
            }
            self.props.showInvisible(self.state.showInvisible);
            self.action.doAction("studio_reload");
        },
    });

    autoScroll([
        document.querySelector('.cy-scrollable-calendar')
    ], {
        margin: 20,
        maxSpeed: 5,
        scrollWhenOutside: true,
        autoScroll: function() {
            // Only scroll when the pointer is down, and there is a child being dragged.
            return this.down && sortable.dragging;
        }
    });
})

    }
    /**
     * undoAction
     *
     * Undo the last performed action by calling the RPC.
     *
     */
    async undoAction(err) {
        try {
            const storage = JSON.parse(sessionStorage.getItem('UndoRedo')) || [];
            const undoElement = storage.pop();
            let view_type = 'calendar'
            let view_id = this.props.viewId
            sessionStorage.setItem('UndoRedo', JSON.stringify(storage));
            const element = document.querySelector('.o_content');
            if (element && element.classList.contains('d-none')) {
                view_id = 'search'
                view_id = this.env.searchModel.searchViewId
            }
            if (undoElement) {
                let redoStack = JSON.parse(sessionStorage.getItem('ReDO')) || [];
                redoStack.push(undoElement);
                sessionStorage.setItem('ReDO', JSON.stringify(redoStack));
                let xPaths = false
                const count = (undoElement.match(/<xpath /g) || []).length;
                if (count >= 2) {
                    xPaths = true
                }

                await this.rpc('cyllo_studio/undo_action', {
                    model: this.props.model.resModel,
                    view_type: view_type,
                    view_id: view_id,
                    xPaths: xPaths,
                });
            }
        } finally {
            this.notification.add({
                title: _t("Validation Error"),
                message: "Unable to Complete The Process.",
                description: err["cause"].toString(),
                type: "notification_panel",
                notificationType: "warning",
            });
            this.action.doAction("studio_reload");
        }
    }

    /**
     * Get available FontAwesome icon classes
     */
    get IconClass() {
        return ICONCLASS
    }
    /**
     * Get available fields for the calendar popover.
     */
    get fields() {
        const popoverFieldNames = new Set(Object.keys(this.props.model.popoverFieldNodes));
        const result = Object.values(this.props.model.fields)
            .filter(function(field) {
                if (field.type == "properties" && !popoverFieldNames.has(field.definition_record)) {
                    return false
                }
                return !popoverFieldNames.has(field.name)
            })
            .map(field => ({
                value: field.name,
                label: field.string
            }));

        return result
    }
       /**
     * Handle icon selection
     * @param {string} icon - FontAwesome class name
     */
    onSelectIcon(icon) {
        this.state.item.options.icon = icon
        this.state.iconToggle = false
    }

     /**
     * Handle field selection
     * @param {Object} field - Selected field object
     */
    onSelectField(field) {
        this.state.dateField = ['datetime', 'date','one2many'].includes(field.type);
        this.state.item.name = field.name
        this.state.item.type = field.type
    }

    /** Add or update the selected widget */
    AddWidgetSelected(value) {
        if (this.state.item.widget) {
            this.state.item.widget = null;
        }
        this.state.item.widget = value
        this.state.widgetSelect = value
    }
    get selectedWidget() {
        return this.state.item.widget
    }

    /** Return widget options for selection */
    Widget() {
        const result = this.widgets.map(item => ({
            value: item[0],
            label: item[1]
        }));
        return [{
            value: false,
            label: '(None)'
        }, ...result]
    }

    /** Return list of compatible widgets for current field type */
    get widgets() {
        let widgets = [];
        let type =
            this.state.item.type == "image" ?
            "binary" :
            this.state.item.type;
        Object.entries(registry.subRegistries.fields.content).forEach(
            ([key, value]) => {
                if (
                    value[1].supportedTypes != undefined &&
                    value[1].supportedTypes.includes(type)
                ) {
                    widgets.push([
                        key,
                        `${value[1].displayName || ""} (${key.split(".").pop()})`,
                    ]);
                }
            }
        );
        return widgets;
    }


    get widgets() {
    const type = this.state.item.type === "image" ? "binary" : this.state.item.type;
    return Object.entries(registry.subRegistries.fields.content)
        .filter(([, value]) => value[1].supportedTypes?.includes(type))
        .map(([key, value]) => [
            key,
            `${value[1].displayName || ""} (${key.split(".").pop()})`
        ]);
    }

    /**
     * Determine if a field node is invisible
     * @param {Object} fieldNode
     * @param {Object} record
     */
    isInvisible(fieldNode, record) {
        if (!fieldNode || !fieldNode.invisible) {
            return false;
        }
        const inv = fieldNode.invisible;
        if (inv === 'true' || inv === 'True' || inv === '1' || inv === true) {
            return true;
        }
        if (inv === 'false' || inv === 'False' || inv === '0' || inv === false) {
            return false;
        }
        try {
            return super.isInvisible(fieldNode, record);
        } catch (_e) {
            return false;
        }
    }

    /** Toggle invisible property via radio button */
    onDomainRadioClick({
        target
    }) {
        this.state.item.invisible = target.checked ? 'True' : 'False'
    }

    /** Open expression editor dialog for domain/invisible expressions */
    onDomainClick() {
        const filteredObj = Object.keys(this.props.model.fields).filter(key => key in this.props.model.meta.activeFields)
            .reduce((acc, key) => {
                acc[key] = this.props.model.fields[key];
                return acc;
            }, {});
        this.addDialog(ExpressionEditorDialog, {
            resModel: this.props.model.resModel,
            fields: this.props.model.fields,
            expression: this.state.item.invisible || 'false',
            onConfirm: (expression) => {
                this.state.item.invisible = expression
            },
        });
    }

    /** Initialize a new field for adding */
    addField() {
        this.state.dateField = false
        this.state.editable = true
        this.state.item = {
            invisible: 'False',
            options: {},
            attrs: {},
            new: true
        }
    }

    /** Prepare editing for an existing field */
    async handleEdit(item) {
        this.state.dateField = ['datetime', 'date', 'one2many'].includes(item.type);
        const relationModel = this.props.model.fields[item.name]?.relation
        if (relationModel) {
            let fields = await this.orm.searchRead("ir.model.fields", [
                ["model", "=", relationModel],
                ["ttype", "=", 'binary']
            ], ["name", "field_description"])
            fields = sortBy(fields, 'field_description')
            this.state.avatarFields = fields.reduce((acc, obj) => {
                acc[obj.name] = obj.field_description;
                return acc;
            }, {});
        }
        this.state.editable = true
        this.state.item = {...item}
        this.state.widgetSelect = item.widget
    }

    onDiscard() {
        this.state.editable = false
        this.state.item = {}
    }

    /** Save changes for the currently edited or added field */
    async onSave() {
        this.env.services.ui.block();

        try {
            if (!this.state.item.name) {
                return this.action.doAction({
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': 'Select a field',
                        'type': 'warning',
                        'sticky': false,
                    }
                })
            }

            const path = this.state.item.MainPath || '/calendar'
            const position = path === '/calendar' ? 'inside' : 'replace'
            if (this.state.item?.options?.icon) {
                this.state.item.options.icon = "fa " + this.state.item.options.icon
            }
            let properties = {
                name: this.state.item.name,
                string: this.state.item.string || this.props.model.fields[this.state.item.name].string,
                options: JSON.stringify(this.state.item.options),
                invisible: this.state.item.invisible || 'False',
            }
            let extra_data = {
                active_fields: this.activeFields,
                model:this.props.model.resModel,
            }

            if (this.state.item.widget) {
                properties.widget = this.state.item.widget
                this.state.item.widget = null;
            }

            if (this.state.item.attrs?.filters) {
                properties.filters = '1'
            }
            if (this.state.item.attrs?.avatar_field) {
                properties.avatar_field = this.state.item.attrs.avatar_field
            }
            const response = await this.rpc("cyllo_studio/calendar/save/item", {
                view_id: this.props.viewId,
                model: this.props.model.resModel,
                path,
                position,
                properties,
                extra_data,
            });
            if (response) {
                let storedArray = JSON.parse(sessionStorage.getItem('UndoRedo')) || [];
                let cleanedStr = response.replace(/\s+/g, ' ').trim();
                storedArray.push(cleanedStr);
                sessionStorage.setItem('UndoRedo', JSON.stringify(storedArray));
                sessionStorage.setItem('ReDO', JSON.stringify([]));
            }
        } finally {
            this.env.services.ui.unblock();
        }
        this.props.showInvisible(this.state.showInvisible)
        this.action.doAction("studio_reload");
        this.state.editable = false;
    }
    /**
     * Get currently active fields in the popover
     */
    get activeFields() {
        return this.props.model.activeFields;
    }
    /**
     * Get mapping of properties fields to their definition records
     */
    get propertiesFieldRelation() {
        const properties = []
        const propertiesField = Object.values(this.activeFields).filter(item => item.type === 'properties')
        for (const rec of propertiesField) {
            properties.push({
                name: rec.name,
                definition: rec.definition_record
            })
        }
        return properties
    }

    async onDelete(path, name) {
        if (this.propertiesFieldRelation.length) {
            const propertiesFields = this.propertiesFieldRelation.filter(item => item.definition === name)
            if (propertiesFields.length) {
                return this.notification.add({
                    title: _t("Warning"),
                    message: "Cant delete this field.",
                    description: "This field is being used as definition for another field",
                    type: "notification_panel",
                    notificationType: "warning",
                    time: 1000,
                })
            }
        }
        this.env.services.ui.block();
        try {
            const response = await this.rpc("cyllo_studio/calendar/remove/item", {
                view_id: this.props.viewId,
                model: this.props.model.meta.resModel,
                path,
            });
            if (response) {
                let storedArray = JSON.parse(sessionStorage.getItem('UndoRedo')) || [];
                let cleanedStr = response.replace(/\s+/g, ' ').trim();
                storedArray.push(cleanedStr)
                sessionStorage.setItem('UndoRedo', JSON.stringify(storedArray));
                sessionStorage.setItem('ReDO', JSON.stringify([]));
            }
        } finally {
            this.env.services.ui.unblock();
        }
        this.action.doAction("studio_reload");
        this.state.editable = false;
    }
}