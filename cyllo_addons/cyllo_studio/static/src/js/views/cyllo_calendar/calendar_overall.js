/** @odoo-module **/

/**
 * CalendarOverall
 *
 * This component manages the overall calendar view configuration in Odoo Studio.
 * Responsibilities include:
 *  - Opening the calendar dialog for a specific record
 *  - Handling visibility toggling of invisible fields
 *  - Managing display modes and scales (Day, Week, Month, Year)
 *  - Updating calendar attributes via RPC calls
 *  - Providing filtered lists of fields for date, integer, boolean, colour, and default display
 *
 * Props:
 *  - model: Object containing calendar metadata and records
 *  - viewId: Numeric ID of the current calendar view
 *  - handleView: Function to handle view switching
 */
import { Component, useState, onWillUpdateProps } from "@odoo/owl";
import { sortBy } from "@web/core/utils/arrays";
import { CylloStudioDropdown } from "@cyllo_studio/js/view_editor/dropdown/CylloStudioDropdown";
import { MultiSelectDropDown } from "@cyllo_studio/js/view_editor/dropdown/multi_select_dropdown/multi_select_dropdown";
import { useService } from "@web/core/utils/hooks";
import { CalendarViewDialog } from "@cyllo_studio/js/views/cyllo_calendar/calendar_field_node_dialog/calendar_field_nodes_dialog";
import { DisplayNotification } from "@cyllo_studio/js/utils/display_notification";
import { CylloRecordSelector } from "@cyllo_studio/js/view_editor/dropdown/record_selector/record_selector";
export class CalendarOverall extends Component {
    static template = "cyllo_studio.CalendarOverall";
    setup() {
        this.action = useService("action");
        this.notification = useService('effect')
        this.rpc = useService("rpc");
        this.dialogService = useService("dialog");
        this.state = useState({
            ...this.state,
            openCalendar: false,
            showInvisible: false,
            calendar_info: this.props.model
        })
        onWillUpdateProps((nextProps) => {
            this.state.calendar_info = nextProps.model
            if (this.state.openCalendar) {
                this.openDialog();
            }
        })
    }
    /**
     * Open the CalendarViewDialog for the first available record
     * Displays a notification if there are no calendar records
     */
    openDialog() {
        this.state.openCalendar = true
        if (Object.values(this.props.model.records).length) {
            this.dialogService.add(CalendarViewDialog, {
                record: Object.values(this.props.model.records)[0] || {},
                model: this.state.calendar_info,
                viewId: this.props.viewId,
                invisible: this.state.showInvisible,
                showInvisible: (invisible)=>this.invisible(invisible),
                close: () => {
                    this.state.openCalendar = false
                },
            })
        } else {
            return DisplayNotification(this, {
                message: "No Calendar Records !!",
                type: 'warning',
                sticky: false,
            })
        }
    }

    /**
     * Toggle visibility of invisible fields
     * @param {boolean} invisible - true to show invisible fields
     */
    invisible(invisible){
        this.state.openCalendar = true
        this.state.showInvisible = invisible
    }

    /**
     * Handle changes to display modes (scales)
     * @param {Array} values - Selected display modes
     * @param {string} scale - Scale to update
     */
    async onDisplayModeChange(values, scale) {
        if(values.includes(scale)){
            return await this.updateCalender('scales', values.join(','))
        }
        return this.action.doAction({
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': "Can't remove Default Display Mode from Display Modes !!!",
                'type': 'warning',
                'sticky': false,
            }
        })
    }

    /** Available calendar scales */
    get scales() {
        return { day: "Day", week: "Week", month: "Month", year: "Year" };
    }

    /**
     * Update a calendar attribute via RPC
     * @param {string} name - Attribute name
     * @param {string} value - Attribute value
     */
    async updateCalender(name, value = "") {
        this.state.openCalendar = false
        try {
            const response = await this.rpc("/cyllo_studio/calendar/update/attributes", {
                name,
                value,
                view_id: this.props.viewId,
                model: this.props.model.meta.resModel,
            });
            if (response) {
                let storedArray = JSON.parse(sessionStorage.getItem('UndoRedo')) || [];
                let cleanedStr = response.replace(/\s+/g, ' ').trim();
                storedArray.push(cleanedStr);
                sessionStorage.setItem('UndoRedo', JSON.stringify(storedArray));
                sessionStorage.setItem('ReDO', JSON.stringify([]));
            }
            } finally {
                this.action.doAction('studio_reload');
            }
            this.action.doAction("studio_reload");
    }

    /** Fields of type date or datetime */
    get dateFields() {
        const dateFields = [];
        for (const [fieldName, field] of Object.entries(this.props.mode.fields)) {
            if (["date", "datetime"].includes(field.type)) {
                dateFields.push({ value: fieldName, label: field.string });
            }
        }
        return sortBy(dateFields);
    }

    /** Fields of type integer or float */
    get intFields() {
		const intFields = [];
		for (const [fieldName, field] of Object.entries(this.props.mode.fields)) {
			if (['integer', 'float'].includes(field.type)) {
				intFields.push({ value: fieldName, label: field.string })
			}
		}
		return [ ['', ''], ...sortBy(intFields) ];
	}

    /** Fields of type boolean */
	get booleanFields() {
		const booleanFields = [];
		for (const [fieldName, field] of Object.entries(this.props.mode.fields)) {
			if (['boolean'].includes(field.type)) {
				booleanFields.push({
					value: fieldName,
					label: field.string
				})
			}
		}
		return [ ['', ''], ...sortBy(booleanFields) ];
	}

    /** Fields suitable for colour mapping */
	get colourFields() {
		const colourFields = [];
		for (const [fieldName, field] of Object.entries(this.props.mode.fields)) {
			if (['many2one', 'selection', 'many2many', 'one2many'].includes(field.type)) {
				colourFields.push({
					value: fieldName,
					label: field.string
				})
			}
		}
		return [ ['', ''], ...sortBy(colourFields, (item) => item[1]) ];
	}

    /** Fields suitable for default display (excludes complex types) */
	get defaultDisplayFields() {
		const defaultDisplayFields = [];
		const excludedTypes = ['one2many', 'many2many', 'many2one', 'binary', 'image', 'json', 'properties_definition', 'reference'];
		for (const [fieldName, field] of Object.entries(this.props.mode.fields)) {
			if (!excludedTypes.includes(field.type)) {
				defaultDisplayFields.push({
					value: fieldName,
					label: field.string
				});
			}
		}
		return sortBy(defaultDisplayFields);
	}

    /**
     * Handle view changes by delegating to parent
     * @param {string} name - View name
     * @param {any} value - Optional value
     */
    handleView(name, value = null) {
        this.state.openCalendar = false
        this.props.handleView(name, value)
    }
}

CalendarOverall.components = {
  CylloStudioDropdown,
  MultiSelectDropDown,
  CalendarViewDialog,
  CylloRecordSelector,
};
