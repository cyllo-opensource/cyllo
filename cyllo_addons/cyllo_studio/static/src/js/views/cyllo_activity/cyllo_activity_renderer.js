/** @odoo-module **/
import { ActivityRenderer } from "@mail/views/web/activity/activity_renderer";
import { CylloActivityRecord } from "./cyllo_activity_record";
import { Component, onMounted, useState, onWillUnmount,onWillDestroy } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { getFormattedRecord, getImageSrcFromRecordInfo, isHtmlEmpty } from "@web/views/kanban/kanban_record";

/**
 * CylloActivityRenderer
 *
 * Extends the base ActivityRenderer to trigger custom activity dialogs
 * and provide a temporary highlight message when the edit button is shown.
 */
export class CylloActivityRenderer extends ActivityRenderer {
	setup() {
		super.setup();
		this.rpc = useService('rpc');
		this.action = useService("action");

		onMounted(async() => {
		    this.env.bus.trigger("ACTIVITY_DETAILS", {
				archInfo: this.props.archInfo,
				model: this.props.resModel,
				viewId: this.env.config.viewId,
				viewType: this.env.config.viewType,
				type:'dialog_box',
				fields: this.props.fields,
				activityResIds: this.props.activityResIds,
				records: this.props.records,
			});
            // Clear stale session record so no modal is re-opened on reload
            sessionStorage.removeItem('ActivityRecordId');
		});
        onWillDestroy(() => {
            this.env.bus.trigger("ACTIVITY_REMOVED", { activity: false });
        });
	}

	/**
     * Show a temporary highlight message for the edit button
     */
	showEditButton(ev) {
		const editButton = document.querySelector('.cy-viewEdits')?.parentElement
		if (!editButton) return;
		const editHighlight = editButton.querySelector('div')

		if (editButton && !editHighlight) {
			editButton.classList.add('edit-highlight')
			const messageDiv = document.createElement('div')
			messageDiv.className = 'cy-activity-edit-message';
			const spanElement = document.createElement('span');
			spanElement.textContent = 'Customise Activity Record';
			messageDiv.append(spanElement);
			editButton.append(messageDiv);

			setTimeout(() => {
				editButton.classList.remove('edit-highlight');
				if (editButton.contains(messageDiv)) {
					editButton.removeChild(messageDiv);
				}
			}, 3000);
		}
	}
}
CylloActivityRenderer.components = {
	...ActivityRenderer.components,
	CylloActivityRecord,
}
CylloActivityRenderer.template = "cyllo_studio.CylloActivityRenderer"