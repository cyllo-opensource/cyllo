/** @odoo-module **/
import {FormController} from "@web/views/form/form_controller";
import {session} from "@web/session";
import {executeButtonCallback} from "@web/views/view_button/view_button_hook";
import {patch} from "@web/core/utils/patch";
import {useService} from "@web/core/utils/hooks";
import {_t} from "@web/core/l10n/translation";
import {deleteConfirmationMessage, ConfirmationDialog} from "@web/core/confirmation_dialog/confirmation_dialog";

const {onMounted, onPatched, onWillStart} = owl;

patch(FormController.prototype, {
    setup() {
        super.setup();
        this.splitView = null;
        this.orm = useService('orm');
        this.orm.call("ir.model", "get_split_view_mode", [this.model.env.searchModel.resModel]).then(result => {
            this.splitView = result[0].list_split_view;
            if (this.splitView) {
                this.canCreate = false;
            }
        });
        this.isEditOn = false;
        onWillStart(async () => {
            this.settingsAccess = await this.user.hasGroup('base.group_system');
        });
        onMounted(() => {
            this.checkSmartButton()
            this.checkAutoEdit()
             if (this.model && this.model.root) {
                this.originalValues = { ...this.model.root.data };
                }
            if (this.rootRef.el.offsetParent && this.rootRef.el.offsetParent.classList.contains('o_content')) {
                var viewTypeElements = this.rootRef.el.querySelector('.o_control_panel_navigation');
                if (viewTypeElements) {
                    viewTypeElements.remove();
                }
                this.rootRef.el.classList.remove('no-smart-button')
                if (this.props.resModel === 'mrp.production') {
                    var formfieldElement = this.rootRef.el.querySelector('.o_form_view .o_group')
                    formfieldElement.style.width = '160%'
                    formfieldElement.style.setProperty('flex-direction', 'column', 'important');
                }
                var invoice_tax_element = this.rootRef.el.querySelector('.oe_subtotal_footer');
                if (invoice_tax_element) {
                    invoice_tax_element.parentElement.style.flex = 'auto'
                }
            }
        })
        onPatched(() => {
            if (this.splitView) {
                if (this.model.config.mode === 'edit') {
                    const titleElements = this.rootRef.el.querySelector('.oe_title')
                    requestAnimationFrame(() => {
                        const textareaElements = this.rootRef.el.querySelector('#name_0');
                        if (!textareaElements) {
                            const textareaElements = this.rootRef.el.querySelector('#name_1');
                        }
                        if (titleElements) {
                            titleElements.style.height = '100px'
                            if (textareaElements) {
                                textareaElements.style.width = 'auto'
                                textareaElements.style.position = 'relative'
                                textareaElements.style.left = '30px'
                            }
                        } else {
                            if (textareaElements) {
                                textareaElements.style.width = 'auto'
                            }
                        }
                    });
                }
            }
        });
        this.is_auto_edit = session.is_auto_edit
    },

    get deleteValidation() {
        return {
            title: _t("Validation Error"),
            body: _t("You cannot delete a record while in split view"),
            cancel: () => {
            },
        };
    },

    async deleteRecord() {
        if (this.splitView) {
            this.dialogService.add(ConfirmationDialog, this.deleteValidation);
        } else {
            super.deleteRecord()
        }
    },

    get modelParams() {
        let res = super.modelParams;
        let mode = this.props.mode || "edit";
        if (this.canEdit) {
            mode = this.env.inDialog ? "edit" : "readonly";
        }
        res.config.mode = mode
        return res
    },

    async edit(ev) {
        this.isEditOn = true;
        await this.model.root.switchMode("edit");
        this.env.bus.trigger("force_edit_o2m");

        if (!this.canEdit) {
            mode = "readonly";
        }
    },

    checkAutoEdit() {
        if (this.is_auto_edit) {
            this.model.root.switchMode("edit")
        }
    },

    async saveButtonClicked(params = {}, ev) {
        this.isEditOn = false;
        const record = this.model.root;
        let saved = false;
        if (this.props.saveRecord) {
            saved = await this.props.saveRecord(record, params);
        } else {
            saved = await record.save(params);
        }
        if (saved && this.props.onSave) {
            this.props.onSave(record, params);
        }
        if (saved && !this.is_auto_edit) {
            await this.model.root.switchMode("readonly");
        }
        if (this.model.config.resModel === 'res.config.settings') {
            return executeButtonCallback(this.ui.activeElement, () => this.save(params));
        }
       if (record && record.model.config.resModel == "res.users") {
            const oldValue = this.originalValues.auto_edit;
            const newValue = record.data.auto_edit;
            if (oldValue !== newValue) {
                window.location.reload();
        }
        }

    },

    async discard() {
        this.isEditOn = false;
        if (this.props.discardRecord) {
            this.props.discardRecord(this.model.root);
            return;
        }
        await this.model.root.discard();
        if (this.props.onDiscard) {
            this.props.onDiscard(this.model.root);
        }
        if (this.model.root.isNew || this.env.inDialog) {
            this.env.config.historyBack();
        }
        if (!this.is_auto_edit) {
            await this.model.root.switchMode("readonly");
        }
    },

    async onPagerUpdate({offset, resIds}) {
        const dirty = await this.model.root.isDirty();
        if (dirty) {
            return this.model.root.save({
                onError: this.onSaveError.bind(this),
                nextId: resIds[offset],
            });
        } else {
            this.checkSmartButton()
            return this.model.load({resId: resIds[offset]});
        }
    },

    checkSmartButton() {
        const isSmartButton = this.rootRef.el.querySelector('.cy-right-sidebar');
        if (!isSmartButton) {
            this.rootRef.el.classList.add('no-smart-button')
        }
    },

    /**Get current view's form_external_id and model. Then Open wizard for create new field*/
    CreateField() {
        this.orm.call('field.create', 'get_xml_ids', [1], {model: this.props.resModel}).then((result) => {
            var form_external_id = result.form_external_id;
            var model = result.model;
            this.env.services.action.doAction({
                type: 'ir.actions.act_window',
                name: _t('Field Creation'),
                res_model: "field.create",
                target: 'new',
                context: {
                    'active_model': this.props.resModel,
                    'default_form_view_external_id': form_external_id,
                    'default_model': model,
                },
                views: [[false, 'form']],
            });
        })
    },

    /**function that creates archive, unarchive, duplicate, delete and Create_field menus in action button*/
    getStaticActionMenuItems() {
        const {activeActions} = this.archInfo;
        return {
            archive: {
                isAvailable: () => this.archiveEnabled && this.model.root.isActive && this.user.isAdmin,
                sequence: 10,
                description: _t("Archive"),
                icon: "ri-archive-line",
                callback: () => {
                    this.dialogService.add(ConfirmationDialog, this.archiveDialogProps);
                },
            },
            unarchive: {
                isAvailable: () => this.archiveEnabled && !this.model.root.isActive && this.user.isAdmin,
                sequence: 20,
                icon: "ri-inbox-unarchive-line",
                description: _t("Unarchive"),
                callback: () => this.model.root.unarchive(),
            },
            duplicate: {
                isAvailable: () => activeActions.create && activeActions.duplicate,
                sequence: 30,
                icon: "ri-file-copy-line",
                description: _t("Duplicate"),
                callback: () => this.duplicateRecord(),
            },
            delete: {
                isAvailable: () => activeActions.delete && !this.model.root.isNew,
                sequence: 40,
                icon: "ri-delete-bin-line",
                description: _t("Delete"),
                callback: () => this.deleteRecord(),
                skipSave: true,
            },
            /* function that show Add a New Field menu in all action button*/
            Create_field: {
                isAvailable: () => this.settingsAccess,
                sequence: 50,
                icon: 'ri-add-line',
                description: _t("Add Field"),
                callback: () => this.CreateField(),
                skipSave: true,
            },
        };
    },
});
