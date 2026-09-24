/** @odoo-module **/

/**
 * CylloField
 *
 * This component extends Odoo's default `Field` class to add
 * custom behavior required for Cyllo Studio's view editor.
 *
 * Key Features:
 * - Parses custom field attributes (e.g., `cy-xpath`, `striped`).
 * - Handles field editing states via event bus.
 * - Manages X2Many field navigation and breadcrumbs.
 * - Triggers property panels for form and kanban fields.
 * - Provides safe field props evaluation (context, domain, readonly, etc.).
 */
import {
    Component,
    useState,
    onMounted,
} from "@odoo/owl";
import {
    Field
} from "@web/views/fields/field";
import {
    getFieldDomain
} from "@web/views/fields/field";
import {
    Domain
} from "@web/core/domain";
import {
    useService
} from "@web/core/utils/hooks";
import {
    patch
} from '@web/core/utils/patch';
import {
    registry
} from "@web/core/registry";
import {
    evaluateExpr,
    evaluateBooleanExpr
} from "@web/core/py_js/py";
import {
    getFieldContext
} from "@web/model/relational_model/utils";
import {
    validateEdit
} from "@cyllo_studio/js/root/studio_wrapper";

/**
 * Helper to evaluate dynamic placeholders like {{field_name}} in a string.
 */
function evaluatePlaceholder(placeholder, record) {
    if (placeholder && typeof placeholder === 'string' && placeholder.includes('{{') && placeholder.includes('}}')) {
        if (record && record.data) {
            return placeholder.replace(/{{(.*?)}}/g, (match, fieldName) => {
                const field = fieldName.trim();
                if (field in record.data) {
                    const value = record.data[field];
                    // If the value is an object (relational), try to find a display name
                    return (value && typeof value === 'object' && 'display_name' in value)
                        ? value.display_name
                        : (value === false || value === undefined) ? '' : value;
                } else {
                    console.warn(`[Cyllo] Dynamic placeholder resolution failed: field "${field}" not found in record data. Available fields:`, Object.keys(record.data));
                }
                return match;
            });
        }
    }
    return placeholder;
}


patch(Field, {
     /**
     * Extend parseFieldNode to support custom attributes like
     * `cy-xpath` and `striped` for Cyllo Studio.
     */
    parseFieldNode() {
        let data = super.parseFieldNode(...arguments);
        const MainPath = arguments[0].getAttribute("cy-xpath");
        data.MainPath = MainPath;
        data.striped = arguments[0].getAttribute("striped") ? "cy-studio-striped" : "";
        return data;
    }
});

patch(Field.prototype, {
    /**
     * Patch fieldComponentProps to evaluate dynamic placeholders in the format {{field_name}}.
     * This allows dynamic placeholders to work in standard views.
     */
    get fieldComponentProps() {
        const props = super.fieldComponentProps;
        props.placeholder = evaluatePlaceholder(props.placeholder, this.props.record);
        return props;
    }
});

export class CylloField extends Field {
    static template = 'cyllo_studio.Field';

    setup() {
        super.setup();
        this.rpc = useService("rpc");
        this.action = useService("action");
        this.orm = useService("orm");
        this.notification = useService("effect");
        this.FieldPlaceholder = false;
        this.state = useState({
            viewActionid: true,
            isEditingButton: false,
            isEditingSmartButton : false,
            isStudioEdit : false,
            isEditingNewButton :false,
        });
        this.cyStudioReadonly = ["ir.model.access", "ir.rule"].includes(this.action.currentController?.action.res_model)
        onMounted(async () => {
            const restorePath = sessionStorage.getItem('RestoreFieldPath');
            if (restorePath && this.props.fieldInfo?.attrs?.["cy-xpath"] === restorePath) {
                sessionStorage.removeItem('RestoreFieldPath');
                setTimeout(() => {
                    const el = document.querySelector(`[cy-xpath="${restorePath}"]`);
                    if (el) {
                        this.onItemClick({ target: el, srcElement: el });
                    }
                }, 100);
            }

            // Check if onViewModeClick has triggered the x2many action
            const x2ManyTriggered = sessionStorage.getItem('CyX2ManyTriggered');
            this.CyX2Many = sessionStorage.getItem('CyX2ManyPath');
            if (x2ManyTriggered === 'true' && this.CyX2Many && this.props.fieldInfo.MainPath === this.CyX2Many) {
                this.CyX2ManyClick(this.fieldComponentProps?.viewMode);
            }
        });
        this.env.bus.addEventListener("BUTTON_EDIT_STARTED", ({ detail }) => {
            this.state.isEditingButton = detail.isEditingButton
        })
        this.env.bus.addEventListener("SMART_BUTTON_EDIT_STARTED", ({ detail }) => {
            this.state.isEditingSmartButton = detail.isEditingSmartButton
        })
        this.env.bus.addEventListener("STUDIO_EDIT_STARTED", ({ detail }) => {
            this.state.isStudioEdit = detail.isStudioEdit
        })
        this.env.bus.addEventListener("NEW_BUTTON_EDIT_STARTED", ({ detail }) => {
            this.state.isEditingNewButton = detail.isEditingNewButton
        })

    }

     /**
     * Compute props to be passed to the underlying field component.
     * Handles readonly, domain, context, required and merges
     * custom Cyllo Studio attributes.
     */
    get fieldComponentProps() {
        const record = this.props.record;
        let readonly = this.props.readonly || false;
        let propsFromNode = {};

        if (this.props.fieldInfo) {
            let fieldInfo = this.props.fieldInfo;
            readonly =
                readonly ||
                evaluateBooleanExpr(fieldInfo.readonly, record.evalContextWithVirtualIds);

            if (this.field.extractProps) {
                if (this.props.attrs) {
                    fieldInfo = {
                        ...fieldInfo,
                        attrs: {
                            ...fieldInfo.attrs,
                            ...this.props.attrs
                        },
                    };
                }

                const dynamicInfo = {
                    get context() {
                        return getFieldContext(record, fieldInfo.name, fieldInfo.context);
                    },
                    domain() {
                        if (fieldInfo.domain) {
                            return new Domain(
                                evaluateExpr(fieldInfo.domain, record.evalContext)
                            ).toList();
                        }
                        return getFieldDomain(record, fieldInfo.name);
                    },
                    required: evaluateBooleanExpr(
                        fieldInfo.required,
                        record.evalContextWithVirtualIds
                    ),
                    readonly: readonly,
                };
                propsFromNode = this.field.extractProps(fieldInfo, dynamicInfo);
                if ('placeholder' in propsFromNode) {
                    propsFromNode.placeholder = evaluatePlaceholder(propsFromNode.placeholder, record);
                }
                // StatusBarField requires foldField to be a string; guard against
                // boolean true saved by older Cyllo builds (fold_field checkbox bug).
                if ('foldField' in propsFromNode && typeof propsFromNode.foldField !== 'string') {
                    propsFromNode.foldField = propsFromNode.foldField ? 'fold' : undefined;
                }
                this.FieldPlaceholder = propsFromNode;
            }
        }

        const props = {
            ...this.props
        };
        delete props.style;
        delete props.class;
        delete props.showTooltip;
        delete props.fieldInfo;
        delete props.attrs;
        delete props.type;
        delete props.readonly;
        delete props.striped;
        delete props.invisible;
        delete props.MainPath;

        return {
            readonly: !this.cyStudioReadonly,
            ...propsFromNode,
            ...props,
        };
    }

    /**
     * Handles click on a field in view mode.
     * Responsible for navigating into X2Many fields,
     * storing navigation state, and triggering view actions.
     */
  async onViewModeClick(ev) {
    let isNotEdit = false;

    this.env.bus.trigger('editListViewClick', {
        isNotEdit: (value) => {
            isNotEdit = value;
        }
    });

    if (!isNotEdit) {
        isNotEdit = true;
    }

    if (isNotEdit) {
        sessionStorage.setItem("X2manyList", false);
        sessionStorage.setItem('UndoRedo', JSON.stringify([]));
        sessionStorage.setItem('ReDO', JSON.stringify([]));

        const {
            tree,
            kanban,
            model
        } = this.props.fieldInfo?.attrs;

        // Get the relational model for one2many/many2many fields
        const relationalModel = await this.orm.searchRead('ir.model.fields', [
            ["model", "=", this.action.currentController.action.res_model],
            ["name", "=", this.props.fieldInfo.name]
        ]);

        const relationModelName = relationalModel[0]?.relation || model;

        const PrevViewData = {
            ActionId: this.action.currentController.action.id,
            ModelName: this.action.currentController.action.name,
            modelId: this.action.currentController.action.res_model,
            ViewId: this.action.currentController.view.type,
            FieldName: this.props.fieldInfo.string,
            RelationModel: relationModelName,
            FieldInfo: {
                name: this.props.fieldInfo.name,
                relation: relationModelName,
                ttype: relationalModel[0]?.ttype
            }
        };
        sessionStorage.setItem('PrevForm', JSON.stringify(PrevViewData));
        sessionStorage.setItem('CyX2ManyTriggered', 'true');
        sessionStorage.setItem('CyX2ManyPath', this.props.fieldInfo.MainPath);

        // ADD THIS: Store the relational model separately for easy access
        sessionStorage.setItem('CyStudioRelationModel', relationModelName);

            if (tree || kanban) {
            const currentUrl = window.location.href;
            localStorage.setItem('X2ManysStudioPage', [currentUrl, true]);
            const viewId = parseInt(tree || kanban);
            this.CyX2ManyClick(this.props.fieldInfo.viewMode, {
                viewId,
                relationModelName,
            });
            this.env.bus.trigger("X2Many-Breadcrumbs", {
                ModelName: this.action.currentController.action.name,
                FieldName: this.props.fieldInfo.string,
            });
           }

            else if (["list", "kanban"].includes(this.fieldComponentProps.viewMode)) {
                        const viewMode = this.fieldComponentProps.viewMode;
                        let view = await this.orm.searchRead('ir.ui.view', [
                            ["model", "=", relationModelName],
                            ["type", "=", "tree"]
                        ]);

            if (!view[0]) {
                const relationModel = await this.orm.searchRead('ir.model', [
                    ["model", "=", relationModelName]
                ]);
                const result = await this.rpc("/cyllo_studio/create/list/view", {
                    method: 'create_list_view',
                    args: [{
                        relationModel
                    }],
                    kwargs: {},
                });
                view = [result];
            }

            if (this.fieldComponentProps.views[viewMode].xmlDoc.getAttribute('cy-xpath') === '/tree') {
                await this.action.doAction({
                    name: view[0]?.name,
                    type: "ir.actions.act_window",
                    res_model: view[0]?.model,
                    views: [
                        [view[0].id, view[0].type]
                    ],
                    target: "current",
                });
            } else {
                // Trigger CyX2ManyClick directly after setting sessionStorage
                this.CyX2ManyClick(this.fieldComponentProps.viewMode);
            }

            this.env.bus.trigger("X2Many-Breadcrumbs", {
                ModelName: this.action.currentController.action.name,
                FieldName: this.props.fieldInfo.string,
            });

            // UPDATE THIS: Pass the relational model
            this.env.bus.trigger("SET_MODEL", {
                relational_model: relationalModel,
                relation_model_name: relationModelName
            });
        }
    }
}
    /**
     * Handle click on a field item.
     * - In form view, triggers "FIELDS_DETAILS" with metadata.
     * - In kanban view, triggers "KANBAN_FIELD_DETAILS".
     */
    async onItemClick(e) {
        const notification = this.notification || useService("notification");

        if (
            !validateEdit(this.state, notification, "isEditingSmartButton", "Smart Button")
//            !validateEdit(this.state, notification, "isStudioEdit", "Editing")
        ) {
            return;
        }

        const element = e.target;
        let item_path = "";
        let has_multipath = "";

        const targetElement = e.target.parentElement;
        const parentDiv = targetElement.closest('.o_wrap_field');
        if (parentDiv || this.props.fieldInfo.viewType === 'form') {
            let item_path = element.getAttribute("cy-xpath") || "";
            let label_xpath = null;
            const labelElement = parentDiv ?
                parentDiv.querySelector('label') :
                (() => {
                    const fieldEl = document.querySelector(`[cy-xpath="${item_path}"]`);
                    if (!fieldEl) return null;

                    // Check previous siblings for label
                    for (let sibling = fieldEl.previousElementSibling; sibling; sibling = sibling.previousElementSibling) {
                        if (sibling.tagName.toLowerCase() === 'label') return sibling;
                    }

                    // Check parent's previous sibling
                    const parentWrapper = fieldEl.closest('div');
                    return parentWrapper?.previousElementSibling?.tagName.toLowerCase() === 'label' ?
                        parentWrapper.previousElementSibling : null;
                })();

            label_xpath = labelElement?.getAttribute('cy-xpath') || null;


            this.env.bus.trigger('FIELDS_DETAILS', {
                name: this.props.fieldInfo.name || "",
                label: this.props.fieldInfo.string || "",
                widget: this.props.fieldInfo.widget || "",
                fieldType: this.props.fieldInfo.type || "",
                context: this.props.fieldInfo.context || "",
                domain: this.props.fieldInfo.domain || "",
                type: "Properties",
                cy_path: this.props.fieldInfo.attrs["cy-xpath"] || "",
                label_path: label_xpath || "",
                placeholder: this.props.fieldInfo.attrs["placeholder"] || "",
                dynamic_placeholder: this.props.fieldInfo.attrs["dynamic_placeholder"] || "",
                help: this.props.fieldInfo.help || "",
                invisible: this.props.fieldInfo.attrs["invisible"] || "",
                required: this.props.fieldInfo.required || "",
                readonly: this.props.fieldInfo.readonly || "",
                edit: true,
                options: {
                    ...(this.props.fieldInfo.options || {}),
                    ...(this.props.fieldInfo.attrs["statusbar_visible"]
                        ? { statusbar_visible: this.props.fieldInfo.attrs["statusbar_visible"] }
                        : {}),
                },
                recordData: this.props.record.data
            });
        } else if (this.props.fieldInfo.viewType === 'kanban') {
            const name = e.target.getAttribute("name") || e.srcElement.parentElement.getAttribute('name');
            const getRestrictAttribute = (el, level = 0) => {
                if (level > 5 || !el) {
                    return false;
                }
                const isRestricted = el.getAttribute('data-restrict');
                if (isRestricted) {
                    return !!isRestricted;
                }
                return getRestrictAttribute(el.parentElement, level + 1);
            };
            this.env.bus.trigger('KANBAN_FIELD_DETAILS', {
                view_id: this.env.config.viewId,
                view_type: this.env.config.viewType,
                active_fields: this.props.record.activeFields || '',
                model: this.action.currentController.props.resModel,
                name: name,
                path: e.target.getAttribute("cy-xpath") || e.target.parentElement.getAttribute('cy-xpath'),
                invisible: this.props.fieldInfo?.invisible || null,
                dynamic_placeholder: this.props.fieldInfo.attrs?.dynamic_placeholder || "",
                isRestricted: getRestrictAttribute(e.target),
                isFieldTag: !!e.target.getAttribute("field-tag"),
                type: "KanbanFieldProperties",
                allfields: this.props.record.fields,
                widget: this.props.fieldInfo.widget || this.props.fieldInfo.attrs?.widget || "",
                recordData: this.props.record.data
            });
        }
    }

     /**
     * Helper to trigger Cyllo Studio X2Many details bus event.
     */
    CyX2ManyClick(view) {
        const args = {
            list: this.props.record.data[this.props.name],
            archInfo: this.props.fieldInfo?.views?.[view],
            resModel: this.env.model?.config.fields[this.props.name].relation,
            relatedFields: this.props.fieldInfo.relatedFields,
            views: this.props.fieldInfo.views,
            viewMode: this.props.fieldInfo.viewMode,
            string: this.props.fieldInfo.string,
            readonly: this.props.readonly,
            isMany2Many: this.props.fieldInfo.type === 'many2many',
            x2Manylist: false
        }
        this.env.bus.trigger('X2ManyDetails', {
            ...args
        });
    }

}
