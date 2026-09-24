/** @odoo-module **/
import {registry} from "@web/core/registry";
import {useBus, useService} from "@web/core/utils/hooks";
import {browser} from "@web/core/browser/browser";
import {Component,useSubEnv,onWillStart,onWillDestroy,useState,useRef,useEffect, mount,onWillUnmount} from "@odoo/owl";
import {RecordSelector} from "@web/core/record_selectors/record_selector";
import {MultiRecordSelector} from "@web/core/record_selectors/multi_record_selector";
import {Select} from "@web/core/tree_editor/tree_editor_components";
import {FileInput} from "@web/core/file_input/file_input";
import {Dialog} from "@web/core/dialog/dialog";
import {_t} from "@web/core/l10n/translation";
import {DomainSelectorDialog} from "@web/core/domain_selector_dialog/domain_selector_dialog";
const ICONCLASS = ['ri-time-line', 'ri-history-fill', 'ri-discuss-line', 'ri-roadster-line', 'ri-calendar-2-line', 'ri-line-chart-line', 'ri-folder-chart-line', 'ri-team-fill', 'ri-user-2-fill', 'ri-pie-chart-2-fill', 'ri-image-2-fill', 'ri-tools-fill', 'ri-store-2-fill', 'ri-notification-3-fill', 'ri-arrow-up-line', 'ri-arrow-right-up-line', 'ri-arrow-left-up-line', 'ri-arrow-up-down-fill', 'ri-medal-line', 'ri-store-3-fill', 'ri-database-line', 'ri-wallet-3-fill', 'ri-coupon-3-line', 'ri-thumb-up-line', 'ri-group-line', 'ri-contacts-book-line', 'ri-global-line', 'ri-funds-box-fill', 'ri-mail-line', 'ri-briefcase-4-line', 'ri-shake-hands-line', 'ri-megaphone-fill', 'ri-pencil-fill', 'ri-bank-card-line', 'ri-contacts-book-2-line', 'ri-book-fill', 'ri-customer-service-fill', 'ri-dashboard-3-line', 'ri-survey-line', 'ri-hand-heart-fill', 'ri-map-pin-line', 'ri-pushpin-fill', 'ri-truck-line', 'ri-filter-fill', 'ri-emotion-happy-line'];
import { CylloStudioDropdown } from "@cyllo_studio/js/view_editor/dropdown/CylloStudioDropdown";
import {CylloRecordSelector} from "@cyllo_studio/js/view_editor/dropdown/record_selector/record_selector";

/**
 * FirstPage is the main Cyllo Studio app creation component.
 * It handles creating new apps or extending existing models,
 * uploading app icons, managing access rights, record rules,
 * and navigating between app creation steps.
 */

export class FirstPage extends Component {
    setup() {
        super.setup();
        this.orm = useService('orm');
        this.inputRef = useRef("file-input");
        this.iconRef = useRef('IconRef')
        this.inputRefButton = useRef("file-input-button");
        this.iconUpload = useRef("icon_upload");
        this.modelName = useRef("model-name");
        this.rpc = useService("rpc")
        this.action = useService("action");
        this.view = useRef("view");
        this.menuService = useService("menu");
        this.action = useService("action");
        this.dialogService = useService("dialog");
        this.state = useState({
            selectedOption: 'None', // Default selected option
            view_mode: 'new',
            resId: false,
            group_ids: [],
            module_id: false,
            group_id: false,
            appname: '',
            related_model_field: '',
            res_group: '',
            view: [],
            default_view: {0: 'tree'},
            set_default_view: 'tree',
            template: 'cyllo_studio_main_content',
            description: '',
            kanban: '',
            tree: true,
            form: '',
            IconImage: 'ri-time-line',
            iconDefault: '',
            className: '',
            iconVisible: false,
            iconSelectionVisible: false,
            isImageUploaded: false,
            imageUrl: '',
            modelname: '',
            showWarning: false,
            imageLabel: false,
            existing: false,
            boxChecked: false,
            condition: false,
            access_rights_data: [],
            record_rules: [],
            showRecordRule: false,
            confirm: false,
            newAccessRights: [],
            newRecordRules: [],
            CurrentElement: false,
            HideLabel: false,
            ModuleCreated: false,
            boxValue: true,
            menu_id: false,
            menu_action_id: false,
            position: 'none',
            position_checkbox: false,
        })
        this.notification = useService("notification")
        onWillStart(async () => {
            this.modelsToChoose = await this.getNoAbstractNoTransient()
        })
    }

    get modelRecordSelectorDomain() {
        const ids = this.modelsToChoose.map((item) => item.id);
        return [['id', 'in', ids]]
    }

    /** Fetch all non-abstract, non-transient models. */
    async getNoAbstractNoTransient() {
        return await this.rpc("/cyllo_studio/get_non_abstract_non_transient_models") || []
    }


    toggleModelDropdown() {
        if (!this.state.ModuleCreated) {
            document.getElementById("PositionModels").classList.toggle("show");
        }
    }

    ModelselectOption(ev) {
        if (!this.state.ModuleCreated) {

            document.getElementById("PositionModels").classList.remove("show");
            if (ev.target.dataset.value === 'existing') {
                this.state.view_mode = 'existing'
                this.state.existing = true
            } else {
                this.state.existing = false
                this.state.view_mode = 'new'
            }
        }
    }

    toggleDropdown() {
        document.getElementById("PositionDropdownOptions").classList.toggle("show");
    }

    selectOption(element) {
        const selectedElement = event.target;
        document.querySelector('.position-dropdown-selected').textContent = selectedElement.textContent;
        this.state.position = selectedElement.getAttribute('data-value')
        document.getElementById("PositionDropdownOptions").classList.remove("show");
    }

    onChangePosition() {
        const PositionCheckbox = this.__owl__.bdom.el.querySelector('#positionCheckbox1');
        if (PositionCheckbox) {
            this.state.position_checkbox = PositionCheckbox.checked;
        }
    }

    _onClickClose() {
        browser.history.go(-1)
    }

    /** Handle uploading and previewing an app icon image. */
    async AppIconUpload(ev) {
        const inputImage = this.inputRef.el;
        const inputRefButton = this.inputRefButton.el;

        let file_from_main;
        let file_from_upload;

        if (inputImage) {
            file_from_main = inputImage.files[0];
        }
        if (inputRefButton) {
            file_from_upload = inputRefButton.files[0];
        }

        this.state.iconDefault = ''
        var self = this

        if (file_from_main) {
            this.state.HideLabel = true
            this.state.imageUrl = URL.createObjectURL(file_from_main)
            const reader = new FileReader();
            reader.onload = async function (e) {
                const binaryData = e.target.result;
                const image = new Image();
                image.src = binaryData;
                self.state.IconImage = binaryData
                self.state.isImageUploaded = true;
            };
            reader.readAsDataURL(file_from_main);
        }

        if (file_from_upload) {
            this.state.imageLabel = true

            this.state.imageUrl = URL.createObjectURL(file_from_upload)
            this.state.HideLabel = true
            const reader = new FileReader();
            reader.onload = async function (e) {
                const binaryData = e.target.result;
                const image = new Image();
                image.src = binaryData;
                self.state.IconImage = binaryData
                self.state.isImageUploaded = true;
            };
            reader.readAsDataURL(file_from_upload);
        }
    }

    setTemplate(newTemplate) {
        sessionStorage.removeItem('cyllo_studio_template')
        this.state.template = newTemplate;
        sessionStorage.setItem('cyllo_studio_template', newTemplate);
    }

    /** Proceed to the next step of app creation. */
    async firstNext() {
        if (this.state.module_id) {
            const [menu] = await this.orm.read('ir.ui.menu', [this.state.module_id], ['id', 'name', 'sequence']);
            if (this.state.position === "before" && menu.sequence === 0) {
                this.notification.add(_t(`You cant add menu before: ${menu.name}!`), {type: "danger"});
                return;
            }
        }
        if (sessionStorage.getItem('cyllo_studio_template')) {
            sessionStorage.removeItem('cyllo_studio_template')
        }
        if (this.state.view_mode === 'new') {
            if (this.state.appname === '') {
                document.getElementById('name').style.borderBottom = '1px solid #FF4B4B';
                this.state.showWarning = true;
                this.notification.add(_t("App name is required!"), {
                    type: "danger",
                });
                return;
            }
            this.state.showWarning = false
        }
        if (this.state.position !== "none" && !this.state.module_id) {
            const position = document.querySelector("#position-arrow")
            position.querySelector('.o-autocomplete--input.o_input').style.borderBottom = '1px solid #FF4B4B';
            this.state.showWarning = true;
            this.notification.add(_t("Please Select the module"), {
                type: "danger",
            });
            return;
        }
        this.state.showWarning = false
        this.setTemplate('table_details')
    }

    onInputName(ev) {
        var input_type = document.getElementById('name');
        if (input_type.value.length > 0) {
            input_type.style.borderBottom = '1px solid #353535';
        }
    }

    PreviousPage() {
        this.setTemplate('cyllo_studio_main_content')
    }

    ModelPage() {
        this.setTemplate('empty_page_templates')
    }

    /** Create or update app and fetch its access rights. */
    async onConfirm() {
        const iconImage = this.state.iconDefault ? this.state.iconDefault : this.state.IconImage
        if (this.state.view_mode === 'new') {
            this.result = await this.rpc("/cyllo_studio/create_app/new_model", {
                method: 'create_app_new_model',
                args: [],
                kwargs: {
                    appname: this.state.appname,
                    GroupId: this.state.group_ids,
                    IconImage: iconImage,
                    model_id: this.state.resId,
                    default_view: this.state.default_view,
                    set_default_view: this.state.set_default_view,
                    model: this.state.modelname,
                    description: this.state.description,
                    view: this.state.view_mode,
                    state: this.state,
                }
            })
            this.state.menu_id = this.result[5]
            this.state.menu_action_id = this.result[0]
            this.setTemplate('security_details')
            this._fetchAccessRights();
        } else {
            this.state.ModuleCreated = true
            this.result = await this.rpc("/cyllo_studio/create_app/existing_model", {
                method: 'create_app_existing_model',
                args: [],
                kwargs: {
                    appname: this.state.appname,
                    IconImage: iconImage,
                    model_id: this.state.resId,
                    default_views: this.state.default_view,
                    set_default_view: this.state.set_default_view,
                    view: this.state.view_mode,
                    state: this.state
                }
            })
            this.setTemplate('security_details')
            await this._fetchAccessRights();
            await this._fetchRecordRules();
            localStorage.setItem("cy_selected_app", this.result[1])
            localStorage.setItem("selectedAppName", this.state.appname)
            this.state.menu_id = this.result[1]
            this.state.menu_action_id = this.result[0]
        }
        this.state.ModuleCreated = true
        document.querySelector('.modal-backdrop').classList.remove('modal-backdrop');
    }
    /** Fetch access rights for the current model. */
    async _fetchAccessRights() {
        try {
            const access_rights = await this.orm.searchRead("ir.model.access", [
                ["model_id", '=', this.state.resId]
            ], ["name", "model_id", "group_id", "perm_read", "perm_write", "perm_create", "perm_unlink"],);
            if (access_rights && this.state.view_mode === 'existing') {
                this.state.access_rights_data = access_rights;
            } else if (access_rights && this.state.view_mode === 'new') {
                const access_rights = await this.orm.searchRead("ir.model.access", [
                    ["model_id", '=', this.result[2]]
                ], ["name", "model_id", "group_id", "perm_read", "perm_write", "perm_create", "perm_unlink"],);
                this.state.access_rights_data = access_rights;
            }
        } catch (error) {
            // Handle error fetching incoming calls
            console.error("Error fetching  Access:", error);
        }
    }

    handleMenuRadio(ev) {
        this.state.position = ev.target.nextElementSibling.innerText
    }

     /** Fetch record rules for the current model. */
    async _fetchRecordRules() {
        try {
            this.state.record_rules = await this.orm.searchRead("ir.rule", [
                ["model_id", '=', this.state.resId]
            ], ["name", "model_id", "groups", "perm_read", "perm_write", "perm_create", "perm_unlink", "domain_force"],);

        } catch (error) {
            // Handle error fetching incoming calls
            console.error("Error fetching  Record rule:", error);
        }
    }

    onMoveRecordRules() {
        var nav_class_record = document.querySelector('.record-nav')
        var nav_class_access = document.querySelector('.access-nav')
        if (nav_class_record) {
            nav_class_record.classList.add('active')
            nav_class_access.classList.remove('active')
            this.state.showRecordRule = true
        }
    }

    onMoveAccess() {
        var nav_class_record = document.querySelector('.record-nav')
        var nav_class_access = document.querySelector('.access-nav')
        if (nav_class_access) {
            this.state.showRecordRule = false
            nav_class_record.classList.remove('active')
            nav_class_access.classList.add('active')
        }
    }


    async deleteAccessRight(ev, accessRightId) {
        try {
            await this.orm.unlink("ir.model.access", [accessRightId]);
            this.state.access_rights_data = this.state.access_rights_data.filter((accessRight) => accessRight.id !== accessRightId);
        } catch (error) {
            console.error("Error deleting access right:", error);
        }
    }

    async deleteRecordRule(recordRuleId) {
        try {
            await this.orm.unlink("ir.rule", [recordRuleId]);
            this.state.record_rules = this.state.record_rules.filter((record_rules) => record_rules.id !== recordRuleId);
        } catch (error) {
            console.error("Error deleting record right:", error);
        }
    }

    CheckedView(ev) {
        var self = this
        var checkbox = ev.target;
        var isChecked = checkbox.checked;
        const checkedCount = this.view.el.querySelectorAll('.ViewCheck:checked').length;
        var tree_checkbox = this.view.el.querySelectorAll('#customCheckbox')
        if (checkbox.value === 'tree' && isChecked) {
            this.state.tree = true
        }

        var form_checkbox = this.view.el.querySelectorAll('#customCheckbox2')
        var kanban_checkbox = this.view.el.querySelectorAll('#customCheckbox3')
        if (checkbox.value === 'kanban' && isChecked) {
            form_checkbox[0].checked = true
            this.state.form = true
            form_checkbox[0].disabled = true
        } else if (checkbox.value === 'form' && !isChecked) {
            if (this.state.kanban) {
                form_checkbox[0].checked = true
                isChecked = true
                this.state.form = true
            }
        } else {
            form_checkbox[0].disabled = false
        }
        if (checkedCount === 0) {
            this.state.set_default_view = ''
            this.state.boxChecked = false
            this.state.boxValue = false
        } else if (this.state.modelname !== '' && this.state.description !== '' && isChecked) {
            this.state.boxChecked = true
            this.state.boxValue = true
        }
        if (this.state.modelname != '' && this.state.description != '' && this.state.boxValue == true) {
            this.state.boxChecked = true
        }
        if (checkedCount > 0) {
            this.state.boxValue = true
            if (this.state.resId && this.state.boxValue == true) {
                this.state.boxChecked = true
            }
        }
        const checked = this.view.el.querySelectorAll('.ViewCheck')
        checked.forEach(function (element, index) {
            if (element.checked) {
                self.state.default_view[index] = element.value;
            } else {
                self.state.default_view = Object.fromEntries(
                    Object.entries(self.state.default_view).filter(([key, value]) => value !== element.value)
                );
            }
        })
    }

    /** Add a new access rights entry in the UI. */
    async add_access_rights() {
        const {newAccessRights} = this.state
        let canCreate = true
        if (newAccessRights.length) {
            const prevAccess = newAccessRights[newAccessRights.length - 1]
            canCreate = !!(prevAccess.name && prevAccess.groupId);
        }
        if (canCreate) {
            this.state.newAccessRights.push({
                name: "",
                modelId: this.state.view_mode === 'new' ? this.result[6] : this.result[5],
                groupId: false,
                permRead: false,
                permWrite: false,
                permCreate: false,
                permDelete: false,
            })
        } else {
            this.notification.add("Please complete the previous line before adding a new one.");
        }
    }

    /** Add a new record rule entry in the UI. */
    async add_record_rule() {
        const {newRecordRules} = this.state
        let canCreate = true
        if (newRecordRules.length) {
            const prevAccess = newRecordRules[newRecordRules.length - 1]
            canCreate = prevAccess.name
        }
        if (canCreate) {
            this.state.newRecordRules.push({
                name: "",
                modelId: this.state.view_mode === 'new' ? this.result[6] : this.result[5],
                groups: [],
                domain_force: "",
                permRead: false,
                permWrite: false,
                permCreate: false,
                permDelete: false,
            })
        } else {
            this.notification.add("Please complete the previous line before adding a new one.");
        }
    }

    onFileUploaded([data]) {
        this.image = data
    }

    onCloseKpiIcon() {
        this.state.iconSelectionVisible = !this.state.iconSelectionVisible;
    }

    /** Select an icon for the app from the icon selector. */
    selectIcon(className) {
        this.state.iconSelectionVisible = !this.state.iconSelectionVisible;
        this.state.iconDefault = className
        this.state.IconImage = ""
        this.state.imageUrl = ''
        var icon_divs = document.getElementById('file-label')
        if (icon_divs) {
            icon_divs.style.display = 'none';
        }
    }

    get IconClass() {
        return ICONCLASS
    }

    /** Close the first page dialog. */
    onClose() {
        this.props.close();
    }

    onCloseConfirm() {
        this.props.close();
    }

    secondNext() {
        let default_field = document.querySelector('.cy-studio-custom-dropdown-default-view');
        let selected_text = default_field.querySelector('.selected-text').innerText;
        if (this.state.set_default_view === '' || selected_text === '') {
            this.notification.add(_t("Set a default view"), {
                type: "danger",
            });
        }
        if (this.state.modelname === '' && this.state.view_mode === 'new') {
            var input_type = document.getElementById('model_name')
            input_type.style.setProperty('border-bottom', '1px solid #FF4B4B', 'important');
            this.notification.add(_t("Model name is required"), {
                type: "danger",
            });
        }
        if (!this.state.resId && this.state.view_mode === 'existing') {
            const parentElement = document.querySelector('.existing-model-name');
            const inputElement = parentElement.querySelector('.o-autocomplete--input');
            inputElement.style.setProperty('border-bottom', '1px solid #FF4B4B', 'important');
            this.notification.add(_t("Model name is required"), {
                type: "danger",
            });
        }


        if (this.state.description === '' && this.state.view_mode === 'new') {
            document.getElementById('name_desc').style.setProperty('border-bottom', '1px solid #FF4B4B', 'important');
            this.notification.add(_t("Model description is required"), {
                type: "danger",
            });
        }
        if (!this.state.boxValue) {
            document.getElementById('customCheckbox').style.setProperty('border-bottom', '1px solid #FF4B4B', 'important');
            this.notification.add(_t("Please select a view type"), {
                type: "danger",
            });
        }
    }

    async onUpdateModule() {
        const iconImage = this.state.iconDefault ? this.state.iconDefault : this.state.IconImage
        if (this.state.view_mode === 'new') {
            this.result = await this.rpc("/cyllo_studio/app/update", {
                method: 'app_update',
                args: [],
                kwargs: {
                    appname: this.state.appname,
                    IconImage: iconImage,
                    model_id: this.result[2],
                    default_view: this.state.default_view,
                    set_default_view: this.state.set_default_view,
                    model: this.state.modelname,
                    description: this.state.description,
                    view: this.state.view_mode,
                    state: this.state,
                    menu_id: this.state.menu_id,
                    menu_action_id: this.state.menu_action_id,
                }
            })

            this.setTemplate('security_details')
        } else {
            this.result = await this.rpc("/cyllo_studio/create_app/existing_model_update", {
                method: 'update_existing_model',
                args: [],
                kwargs: {
                    appname: this.state.appname,
                    IconImage: iconImage,
                    model_id: this.state.resId,
                    default_views: this.state.default_view,
                    set_default_view: this.state.set_default_view,
                    view: this.state.view_mode,
                    state: this.state,
                    menu_id: this.state.menu_id,
                    menu_action_id: this.state.menu_action_id,
                }
            })
            this.setTemplate('security_details')
        }
        localStorage.setItem("cy_selected_app", this.result[5])
        localStorage.setItem("selectedAppName", this.state.appname)
    }

    onUpdate(resId, self) {
        self.state.resId = resId
        if (!self.state.resId) {
            self.state.boxChecked = false
        }
        if (self.state.resId && self.state.boxValue) {
            self.state.boxChecked = true
        }
    }

    onInputDescription(ev) {
        var input_type = document.getElementById('name_desc');
        if (input_type.value === '') {
            this.state.boxChecked = false
        }
        if (this.state.modelname !== '' && this.state.description !== '' && this.state.boxValue) {
            this.state.boxChecked = true
        }
        if (input_type.value.length > 0) {
            input_type.style.borderBottom = '1px solid #353535';
        }
        var specialCharPattern = /[!@#$%^&*()?":{}|<>]/;
        if (specialCharPattern.test(input_type.value)) {
            this.notification.add(_t("Special characters are not allowed"), {
                type: "danger",
            });
        }
    }

    onInputModelName(ev) {
        var input_type = document.getElementById('model_name');
        if (input_type.value === '') {
            this.state.boxChecked = false
        }
        if (this.state.modelname !== '' && this.state.description !== '' && this.state.boxValue) {
            this.state.boxChecked = true
        }
        var specialCharPattern = /[!@#$%^&*(),?":{}|<>]/;
        if (input_type.value.length > 0) {
            input_type.style.borderBottom = '1px solid #353535';
        }
        if (specialCharPattern.test(input_type.value)) {
            this.notification.add(_t("Special characters are not allowed"), {
                type: "danger",
            });
        }
    }

    firstPrevious() {
        this.setTemplate('cyllo_studio_main_content')
        var icon_divs = document.querySelector('upload-div')
    }

    lastPrevious() {
        this.setTemplate('table_details')
    }

    fieldsDomain(index, isNew = true) {
        this.dialogService.add(DomainSelectorDialog, {
            resModel: this.state.view_mode === 'new' ? this.result[1] : this.result[2],
            domain: isNew ? this.state.newRecordRules[index].domain_force : this.state.record_rules[index].domain_force,
            onConfirm: (domain) => this.domainConfirm(index, isNew, domain),
            disableConfirmButton: (domain) => domain === `[]`,
            title: ("Domain"),
        });
    }

    domainConfirm(index, isNew, domain) {
        if (isNew) {
            this.state.newRecordRules[index].domain_force = domain
        } else {
            this.state.record_rules[index].domain_force = domain
        }
    }

    /** Finalize module creation and update all access rights and record rules. */
    async lastContinue() {
        const modelId = this.state.view_mode === 'new' ? this.result[2] : this.result[4];
        const accessRightIds = this.state.access_rights_data.map(obj => obj.id)
        await this.orm.call('ir.model.access', 'update_access_rights', [accessRightIds, this.state.access_rights_data]);
        const recordRulesIds = this.state.record_rules.map(obj => obj.id)
        await this.orm.call('ir.rule', 'update_record_rules', [recordRulesIds, this.state.record_rules]);
        await this.orm.call('ir.model', 'create_access_right', [modelId, this.state.newAccessRights]);
        await this.orm.call('ir.model', 'create_record_rule', [modelId, this.state.newRecordRules]);
        document.querySelector('.modal-backdrop')?.classList.remove('modal-backdrop');
        this.props.close();
        this.action.doAction('studio_reload')
        localStorage.setItem("isSidebarOn", false)
        window.location.hash = `menu_id=${this.state.menu_id}`;
        window.location.reload();
    }

    get DefaultView() {
        const arr = []
        for (let value in this.state.default_view) {
            const obj = {
                value: this.state.default_view[value],
                label: this.state.default_view[value] === 'tree' ? 'Tree' : this.state.default_view[value]
            }
            arr.push(obj)
        }
        return arr
    }

    get defaultViewType() {
        return this.state.set_default_view
    }

    handleDefaultView(value) {
        this.state.set_default_view = value
    }
}

FirstPage.template = "cyllo_studio.MainPage";
FirstPage.components = {
    ...FirstPage.components,
    Dialog,
    RecordSelector,
    MultiRecordSelector,
    FileInput,
    CylloStudioDropdown,
    CylloRecordSelector
};

FirstPage.props = {
    close: Function,
    title: {
        type: String,
        optional: true
    },
};
FirstPage.defaultProps = {
    title: _t("Cyllo Studio"),
};