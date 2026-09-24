/** @odoo-module **/

/**
 * CylloActivityRecord Component
 *
 * Extends the base ActivityRecord to allow custom rendering, drag-and-drop
 * editing, and interaction with the Cyllo Studio Activity Popover.
 */
import { ActivityRecord } from "@mail/views/web/activity/activity_record";
import { Component, onMounted, onPatched, onWillUpdateProps, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { sortBy } from "@web/core/utils/arrays";
import { useViewCompiler } from "@web/views/view_compiler";
import { CylloActivityCompiler } from "./cyllo_activity_compiler";
import { registry } from "@web/core/registry";
import {getRawValue, getImageSrcFromRecordInfo } from "@web/views/kanban/kanban_record"
const formatters = registry.category("formatters");

export class CylloActivityRecord extends ActivityRecord {
	setup() {
		super.setup();
		this.rpc = useService("rpc");
		this.action = useService("action");
		this.dialogService = useService("dialog");
		var self = this;
		this.state = useState({
			...this.state,
		})
		const { templateDocs } = this.props.archInfo;
		const templates = useViewCompiler(CylloActivityCompiler, templateDocs);
		this.recordTemplate = templates["activity-box"];

		onWillUpdateProps((nextProps) => {
			// This instance is patched in place (no t-key) across Studio
			// auto-save updates, so the compiled template must be rebuilt from
			// the fresh archInfo to reflect new bold/muted/display attributes.
			if (nextProps.archInfo) {
				const nextTemplates = useViewCompiler(CylloActivityCompiler, nextProps.archInfo.templateDocs);
				this.recordTemplate = nextTemplates["activity-box"];
			}
		});

		// Notify ActivityPopover (which owns Sortable/highlight setup for the
		// preview) every time THIS component's own rendered DOM is created or
		// rebuilt — the one reliable signal for "the field nodes changed".
		onMounted(() => this.env.bus.trigger("ACTIVITY_RECORD_RENDERED"));
		onPatched(() => this.env.bus.trigger("ACTIVITY_RECORD_RENDERED"));
	}

	handleFieldWidgetClick(el,fieldName, path) {
		this.env.bus.trigger("ActivityFieldDetails", {
			attributes: el,
			widget: true,
			fieldName: fieldName,
			path: path
		});
	}

	handleFieldClick(el, fieldName, path) {
		this.env.bus.trigger("ActivityFieldDetails", {
			attributes: el,
			fieldName: fieldName,
			path: path
		});
	}

    /**
     * Get the formatted value of a field using registered formatters
     */
	getValue(record, fieldName) {
		const field = record.fields[fieldName];
		const value = record.data[fieldName];
		const formatter = formatters.get(field.type, String);
		return formatter(value, { field, data: record.data }) || field['string'];
	}

    /**
     * Format the record for rendering with the compiled template
     */
	getFormattedRecord(record) {
		const formattedRecord = {
			id: {
				value: record.resId,
				raw_value: record.resId,
			},
		};

		for (const fieldName of record.fieldNames) {
			formattedRecord[fieldName] = {
				value: this.getValue(record, fieldName),
				raw_value: getRawValue(record, fieldName),
			};
		}
		return formattedRecord;
	}

	getRenderingContext() {
		const { record } = this.props;
		return {
			record: this.getFormattedRecord(record),
			activity_image: (...args) => getImageSrcFromRecordInfo(record, ...args),
			user_context: this.user.context,
			widget: this.widget,
			luxon,
			__comp__: Object.assign(Object.create(this), {
				this: this
			}),
		};
	}
}

CylloActivityRecord.props = {
	...ActivityRecord.props,
	openRecord: { type: Function, optional: true }
}

CylloActivityRecord.defaultProps = {
	...ActivityRecord.defaultProps,
}
CylloActivityRecord.components = {
	...ActivityRecord.components,
}
CylloActivityRecord.template = "cyllo_studio.CylloActivityRecord"