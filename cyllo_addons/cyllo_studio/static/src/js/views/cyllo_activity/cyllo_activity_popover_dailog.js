/** @odoo-module **/

/**
 * ActivityPopover Component
 *
 * Handles displaying and editing fields in a Kanban activity record.
 * Supports drag & drop reordering, adding, editing, saving, and deleting fields.
 */
import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { evaluateBooleanExpr } from "@web/core/py_js/py";
import { Field } from "@web/views/fields/field";
import { Record } from "@web/model/record";
import { Component, useExternalListener, onMounted, onWillStart, useState, onWillDestroy } from "@odoo/owl";
import { useViewCompiler } from "@web/views/view_compiler";
import { CylloActivityCompiler } from "./cyllo_activity_compiler";
import { Select } from "@web/core/tree_editor/tree_editor_components";
import { CylloStudioDropdown } from "@cyllo_studio/js/view_editor/dropdown/CylloStudioDropdown";
import { useService, useOwnedDialogs, useBus } from "@web/core/utils/hooks";
import { ExpressionEditorDialog } from "@web/core/expression_editor_dialog/expression_editor_dialog";
import { CylloActivityRecord } from "./cyllo_activity_record";
import { handleUndoRedo } from "@cyllo_studio/js/utils/undo_redo_utils";

export class ActivityPopover extends Component {
	setup() {
		this.rpc = useService("rpc");
		this.action = useService("action");
		this.actionService = useService("action");
		this.notification = useService("effect");
		this.dialogService = useService("dialog");
		this.addDialog = useOwnedDialogs();
		this.state = useState({
			string: "",
			selectedField: "",
			attribute: {},
			selectedFieldAttribute: "",
			fieldName: "",
			editable: false,
			path: "",
			showInvisible: this.props.invisible,
			item: {},
			widget: false
		})

		onWillDestroy(() => {
			if (this._isAutoSaving) {
				// Panel destroyed for preview refresh — parent keeps edit:true, restore on remount
				return;
			}
			if (this.save) {
				sessionStorage.setItem('ActivityRecordId', this.props.records[0]?.resId);
			}
			if (this.props.updateState) {
				this.props.updateState("editButton", true);
				this.props.updateState("edit", false);
			}
		});


		const { templateDocs } = this.props.archInfo;
		const templates = useViewCompiler(CylloActivityCompiler, templateDocs);
		this.recordTemplate = templates["activity-box"];

		// CylloActivityRecord (the child that actually owns/rebuilds the preview
		// DOM) fires this on its own onMounted/onPatched — the reliable signal
		// for "the field nodes were just (re)created", regardless of exactly
		// how many render cycles that took to propagate down from archInfo.
		useBus(this.env.bus, 'ACTIVITY_RECORD_RENDERED', () => {
			this.highlightSelectedField();
			this.initSortable();
		});

		onMounted(() => {
			// Restore editable state after auto-save re-render
			const savedState = sessionStorage.getItem('ActivityEditState');
			if (savedState) {
				try {
					const { path, fieldName, attribute, widget } = JSON.parse(savedState);
					sessionStorage.removeItem('ActivityEditState');
					this.state.editable = true;
					this.state.path = path;
					this.state.fieldName = fieldName;
					this.state.attribute = attribute;
					this.state.widget = widget;
					this.highlightSelectedField();
				} catch (e) {
					sessionStorage.removeItem('ActivityEditState');
				}
			}

			this.initSortable();
		})
		this.env.bus.addEventListener('ActivityFieldDetails', (ev) => {
			this.state.widget = ev.detail.widget
			this.state.editable = true
			this.state.attribute = ev.detail.attributes,
				this.state.fieldName = ev.detail.fieldName,
				this.state.path = ev.detail.path
			this.highlightSelectedField();
		});
	}

	get activityProps() {
		state: this.state
	}

	/**
	 * (Re)attach Sortable to the preview's current field container. Must be
	 * called after every DOM rebuild — Sortable binds to the live node, and
	 * the preview's nodes get recreated whenever the compiled template
	 * refreshes while this component stays mounted (see cyllo_activity_record.js).
	 */
	initSortable() {
		const self = this;
		const activityEl = document.querySelector(".cy-activity");
		if (!activityEl) return;

		// Group every cy-xpath-carrying field by its direct parent. Fields
		// aren't necessarily all siblings under one shared container (e.g. an
		// inline field can sit one level deeper than a full-width row), so
		// every such group gets its own Sortable instance instead of picking
		// a single "winner" container and leaving the rest undraggable.
		const fieldEls = activityEl.querySelectorAll('[cy-xpath]');
		const childrenByParent = new Map();
		fieldEls.forEach((field) => {
			const parent = field.parentElement;
			if (!parent) return;
			if (!childrenByParent.has(parent)) {
				childrenByParent.set(parent, 0);
			}
			childrenByParent.set(parent, childrenByParent.get(parent) + 1);
		});

		if (!this._sortableContainers) {
			this._sortableContainers = new Set();
		}
		// Drop bookkeeping for containers no longer in the document.
		this._sortableContainers.forEach((container) => {
			if (!container.isConnected) {
				this._sortableContainers.delete(container);
			}
		});

		childrenByParent.forEach((count, container) => {
			if (count < 2) return; // nothing to reorder among a single item
			if (this._sortableContainers.has(container) && Sortable.get(container)) {
				return; // already correctly initialized on this exact node
			}
			this._sortableContainers.add(container);

			const existingSortable = Sortable.get(container);
			if (existingSortable) existingSortable.destroy();

			Sortable.create(container, {
				animation: 150,
				ghostClass: 'sortable-ghost',

				onEnd: async function (evt) {
					const el = evt.item;
					const path = el.getAttribute("cy-xpath");
					const parent = container.getAttribute("cy-xpath");

					// Anchor on whichever neighbor is present: insert before the
					// element now following the drop, or — if dropped at the end
					// — after the element now preceding it.
					const next_path = el.nextElementSibling?.getAttribute("cy-xpath") || null;
					const prev_path = el.previousElementSibling?.getAttribute("cy-xpath") || null;
					const position = next_path ? "before" : "after";
					const sibling_path = next_path || prev_path;

					self.env.services.ui.block();
					try {
						const response = await self.rpc("cyllo_studio/activity/move/field", {
							method: 'move_activity_field',
							view_id: self.props.viewId,
							model: self.props.model,
							path,
							position,
							sibling_path,
							parent,
						});
						if (response) {
							handleUndoRedo(response);
						}
					} finally {
						self.env.services.ui.unblock();
					}
					self.save = true;
					self.env.bus.trigger("RENDER_LOAD");
				},
			});
		});
	}

	/**
	 * Mark only the field currently being edited with a persistent
	 * border, clearing it from any previously marked field.
	 */
	highlightSelectedField() {
		const activityEl = document.querySelector(".cy-activity");
		if (!activityEl) return;
		activityEl.querySelectorAll(".cy-field-selected").forEach((el) => {
			el.classList.remove("cy-field-selected");
		});
		if (!this.state.path) return;
		activityEl.querySelectorAll("[cy-xpath]").forEach((el) => {
			if (el.getAttribute("cy-xpath") === this.state.path) {
				el.classList.add("cy-field-selected");
			}
		});
	}

	get allFields() {
		const allFields = Object.entries(this.props.fields).map((field) => {
			return { label: field[1].string + ' (' + field[0] + ')', value: field[0] }
		})
		return allFields;
	}

	updatedField(v) {
		this.state.selectedField = v
	}

	get fieldsDisplay() {
		return [{ label: 'Full', value: 'full' }, { label: 'Right', value: 'right' }, { label: 'Left', value: 'left' }];
	}

	get displayValue() {
		return this.state.attribute?.display || ""
	}

	updatedFieldDisplay(v) {
		this.state.selectedFieldAttribute = v;
		this.autoSave();
	}

	handleFieldBold(ev) {
		this.state.attribute.bold = ev.target.checked;
		this.autoSave();
	}

	handleFieldMuted(ev) {
		this.state.attribute.muted = ev.target.checked;
		this.autoSave();
	}

	async autoSave() {
		try {
			const response = await this.rpc("cyllo_studio/activity/save/field", {
				view_id: this.props.viewId,
				model: this.props.model,
				fieldDisplay: this.state.selectedFieldAttribute || this.state.attribute?.display,
				fieldBold: this.state.attribute.bold === "False" ? 'false' : this.state.attribute.bold,
				fieldMuted: this.state.attribute.muted,
				path: this.state.path,
			});
			if (response) {
				handleUndoRedo(response);
			}
		} catch (e) {
			// silent
		}
		this.save = true;
		// Persist editable state so it survives the re-render
		sessionStorage.setItem('ActivityEditState', JSON.stringify({
			path: this.state.path,
			fieldName: this.state.fieldName,
			attribute: this.state.attribute,
			widget: this.state.widget,
		}));
		this._isAutoSaving = true;
		this.env.bus.trigger("RENDER_LOAD", { keepEdit: true });
	}

	onDiscard() {
		this.state.editable = false;
		this.state.selectedField = "";
		this.state.path = "";
		this.highlightSelectedField();
	}

	/**
	 * Close the activity aside bar (X button), matching the standard
	 * AsideBar close behavior used by the other view editors.
	 */
	closeAside() {
		this.env.bus.trigger("CLEAR-MENU", { fromClose: true });
		if (this.props.updateState) {
			this.props.updateState("editButton", true);
			this.props.updateState("edit", false);
		}
		this.action.doAction("studio_reload");
	}

	async onSave() {
		this.env.services.ui.block();
		try {
			const response = await this.rpc("cyllo_studio/activity/save/field", {
				view_id: this.props.viewId,
				model: this.props.model,
				fieldDisplay: this.state.selectedFieldAttribute || this.state.attribute?.display,
				fieldBold: this.state.attribute.bold === "False" ? 'false' : this.state.attribute.bold,
				fieldMuted: this.state.attribute.muted,
				path: this.state.path,
			});
			if (response) {
				handleUndoRedo(response);
			}
		} finally {
			this.env.services.ui.unblock();
		}
		this.save = true;
		this.state.editable = false;
		this.env.bus.trigger("RENDER_LOAD");
	}

	async onDelete() {
		const fieldNodes = this.props.archInfo.fieldNodes;
		const nameExists = Object.keys(fieldNodes).filter(element => element.startsWith(this.state.fieldName));
		let isPathIncluded = nameExists.some(name => fieldNodes[name].MainPath.includes('/activity/field'));
		let fieldName = isPathIncluded ? "" : this.state.fieldName

		this.env.services.ui.block();
		try {
			const response = await this.rpc("cyllo_studio/activity/remove/field", {
				view_id: this.props.viewId,
				model: this.props.model,
				path: this.state.path,
				field_name: fieldName,
			});
			if (response) {
				handleUndoRedo(response)
			}
		} finally {
			this.env.services.ui.unblock();
		}
		this.action.doAction("studio_reload");
		this.save = true
		this.state.editable = false;
	}

	/**
	 * Reset the current activity view to its code-defined default,
	 * discarding ALL Studio customizations on it. Confirms first.
	 */
	resetView() {
		const model = this.props.model;
		const view_id = this.props.viewId;
		const view_type = this.props.viewType;
		if (!model || !view_id || !view_type) {
			this.notification.add({
				title: _t("Cannot Reset"),
				message: "Open the view you want to reset first.",
				type: "notification_panel",
				notificationType: "warning",
				animation: false,
			});
			return;
		}
		this.dialogService.add(ConfirmationDialog, {
			title: _t("Reset View to Default"),
			body: _t(
				"This removes ALL Studio changes on this view and restores the "
				+ "original layout defined in code. Custom fields you added stay on "
				+ "the model but will no longer appear here."
			),
			confirmLabel: _t("Reset View"),
			cancelLabel: _t("Cancel"),
			confirm: async () => {
				try {
					await this.rpc("/cyllo_studio/reset_view", {
						model: model,
						view_type: view_type,
						view_id: view_id,
					});
				} finally {
					sessionStorage.removeItem("UndoRedo");
					sessionStorage.removeItem("ReDO");
					this.env?.bus?.trigger?.("resetProperties");
					this.actionService.doAction("studio_reload");
					window.location.reload();
				}
			},
			cancel: () => { },
		});
	}

	async addActivityField() {
		if (!this.state.selectedField) {
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
		const container = document.querySelector(".o_activity_record")
		const path = container.firstElementChild.getAttribute('cy-xpath')

		const response = await this.rpc("cyllo_studio/add/activity/field", {
			method: 'add_activity_field',
			view_id: this.props.viewId,
			view_type: this.props.viewType,
			model: this.props.model,
			path,
			name: this.state.selectedField
		});
		if (response) {
			handleUndoRedo(response)
		}
		this.save = true
		this.env.bus.trigger("RENDER_LOAD");
		//        this.action.doAction("studio_reload");
	}
}

ActivityPopover.components = {
	Dialog,
	Field,
	Record,
	Select,
	CylloStudioDropdown,
	CylloActivityRecord
};

ActivityPopover.template = "cyllo_studio.CylloActivityPopover";
