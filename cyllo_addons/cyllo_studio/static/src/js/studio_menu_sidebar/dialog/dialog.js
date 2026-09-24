/** @odoo-module */
import { Dialog } from "@web/core/dialog/dialog";
import { MultiRecordSelector } from "@web/core/record_selectors/multi_record_selector";
import { RecordSelector } from "@web/core/record_selectors/record_selector";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Component, useState, useRef, onMounted, useEffect } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { CheckBox } from "@web/core/checkbox/checkbox";
import {_t} from "@web/core/l10n/translation";
import {ConfirmationDialog} from "@web/core/confirmation_dialog/confirmation_dialog";
import {CylloRecordSelector} from "@cyllo_studio/js/view_editor/dropdown/record_selector/record_selector";
const ICONCLASS = ['ri-time-line', 'ri-history-fill', 'ri-discuss-line', 'ri-roadster-line', 'ri-calendar-2-line', 'ri-line-chart-line', 'ri-folder-chart-line', 'ri-team-fill', 'ri-user-2-fill', 'ri-pie-chart-2-fill', 'ri-image-2-fill', 'ri-tools-fill', 'ri-store-2-fill', 'ri-notification-3-fill', 'ri-arrow-up-line', 'ri-arrow-right-up-line', 'ri-arrow-left-up-line', 'ri-arrow-up-down-fill', 'ri-medal-line', 'ri-store-3-fill', 'ri-database-line', 'ri-wallet-3-fill', 'ri-coupon-3-line', 'ri-thumb-up-line', 'ri-group-line', 'ri-contacts-book-line', 'ri-global-line', 'ri-funds-box-fill', 'ri-mail-line', 'ri-briefcase-4-line', 'ri-shake-hands-line', 'ri-megaphone-fill', 'ri-pencil-fill', 'ri-bank-card-line', 'ri-contacts-book-2-line', 'ri-book-fill', 'ri-customer-service-fill', 'ri-dashboard-3-line', 'ri-survey-line', 'ri-hand-heart-fill', 'ri-map-pin-line', 'ri-pushpin-fill', 'ri-truck-line', 'ri-filter-fill', 'ri-emotion-happy-line'];

/**
 * Component for creating a new menu item.
 * Handles form state, validation, and RPC calls to create the menu in the backend.
 */

export class MenuCreationDialog extends Component {
    setup() {
        var self = this
        this.orm = useService("orm");
        this.action = useService("action");
        this.menuService = useService("menu");
        this.rpc = useService("rpc");
        this.menuRef = useRef('menuRef')
        this.dialog = useService("dialog");
        this.state = useState({
            resId: false,
            actionID: false,
            ActionType: false,
            ParentMenu: this.props.ParentMenu ? this.props.ParentMenu : this.menuService.getCurrentApp()?.id ?? false,
            group_ids: [],
            MenuParent: false,
            ActiveMenu: true,
            model_name: '',
            boxChecked : false,
            description : '',
            menuResId:false,
            IconImage: 'ri-time-line',
        })
        this.state.ParentMenus = this.orm.searchRead('ir.ui.menu',
            []
            , ['id', 'name', 'groups_id', 'active']).then(data => {});

        this.notification = useService("notification");

        onMounted(() => {
            const modalHeader = document.body.querySelector('.modal-header');
            modalHeader.setAttribute('class', 'modal-header-no-drag');
            const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
        })
    }
      /**
     * Updates the resId state for the selected menu item.
     */
    onUpdate(resId, self) {
        self.state.resId = resId
    }

    /**
     * Validates and handles user input for the model name.
     * Prevents special characters and updates the state for checkbox activation.
     */

    onInputModelName(ev) {
        var input_type = document.getElementById('model_name');
        if (input_type.value == '') {
            this.state.boxChecked = false
        }
        if (this.state.modelname != '' && this.state.description != '' && this.state.boxValue == true) {
            this.state.boxChecked = true
        }
        var specialCharPattern = /[!@#$%^&*(),?":{}|<>]/;
        if (input_type.value.length>0){
            input_type.style.borderBottom = '1px solid #353535';
        }
        if (specialCharPattern.test(input_type.value)) {
            this.notification.add(_t("Special characters are not allowed"), {
                type: "danger",
            });
        }
    }

    /**
     * Validates and handles user input for the menu description.
     * Prevents special characters and updates the checkbox state.
     */

    onInputDescription(ev) {
        var input_type = document.getElementById('name_desc');
        if (input_type.value == '') {
            this.state.boxChecked = false
        }
        if (this.state.modelname != '' && this.state.description != '' && this.state.boxValue == true) {
            this.state.boxChecked = true
        }
        if (input_type.value.length>0){
            input_type.style.borderBottom = '1px solid #353535';
        }
        var specialCharPattern = /[!@#$%^&*()?":{}|<>]/;
        if (specialCharPattern.test(input_type.value)) {
            this.notification.add(_t("Special characters are not allowed"), {
                type: "danger",
            });
        }
    }
    /**
     * Confirms menu creation via RPC and reloads the page.
     * If menu name is empty, shows an AlertDialog.
     */
    async OnclickConfirmDialogue(ev){
        if (document.querySelector('.menu-name').value) {
            const data = await this.rpc("/cyllo_studio/menuitem/confirm", {
                method: 'menu_confirm',
                args: [],
                kwargs: {
                    menuName: document.querySelector('.menu-name').value,
                    isParent: this.state.MenuParent,
                    ActiveMenu: this.state.ActiveMenu,
                    ParentMenu: this.state.ParentMenu,
                    groups: this.state.group_ids,
                    ActionType: this.state.ActionType,
                    ActionModel: this.state.actionID,
                    resId : this.state.resId,
                    model_name: this.state.model_name,
                    description : this.state.description,
                    menuResId: this.state.menuResId,
                    IconImage: this.state.IconImage
                }
            })
            this.props.close()
            this.action.doAction('studio_reload')
            window.location.reload()
            return data
        } else {
            var message = "Menu Name is required";
            this.dialog.add(AlertDialog, { body: message });
        }
    }
    /**
     * Opens a dialog to create a child menu item.
     */
    addChild(ev, ParentMenu) {
        if(!ParentMenu && !this.menuService.getCurrentApp()?.id){
            return this.notification.add({
                    title: _t("Validation Error"),
                    message: "Unable to complete the process.",
                    description: "You can't add menu to this model",
                    type: "notification_panel",
                    notificationType: "warning",
                });
        }
        var data = this.dialog.add(MenuCreationDialog, {
            isParent: "sibling",
            title: 'Menu Items Creation',
            ParentMenu: ParentMenu ? ParentMenu.id : this.menuService.getCurrentApp().id
        });
    }

    static template = "cyllo_studio.MenuCreationDialog";
    static props = {
        title: {
            validate: (m) => {
                return (
                    typeof m === "string" || (typeof m === "object" && typeof m.toString === "function")
                );
            },
            optional: true,
        },
        isParent: { type: String, optional: true },
        actionModel: { type: String, optional: true },
        ParentMenu: { type: Number, optional: true },
        close: { type: Function, optional: true},
        isCreate: { type: Boolean, optional: true}
    };
    static defaultProps = {
        title: "Menu Items Creation"
    };
    static components = { Dialog, MultiRecordSelector, RecordSelector, CheckBox, CylloRecordSelector };
}

export class MenuConfigurationDialog extends Component {
    async setup() {
        var self = this
        this.orm = useService("orm");
        this.action = useService("action");
        this.rpc = useService("rpc");
        this.menuService = useService("menu");
        this.data = {}
        this.selectionValuesRef = useRef('cy-MenuSiblings')
        this.dialogService = useService("dialog")
        this.notification = useService("effect")
        this.state = useState({
            group_ids: [],
            menuName: this.props.menuName || "",
            ActiveMenu: this.props.Menu.active ? this.props.Menu.active : false,
            actionID: this.props.Menu.actionID || false,
            ActionType: this.props.Menu.actionModel || false,
            SiblingPosition: {},
            ParentChange: false,
            menuDetails: false,
            ChildParentMenu: false,
            ParentMenu: this.props.ParentMenu ? this.props.ParentMenu : this.menuService.getCurrentApp(),
            Parents: [],
            types:'',
        })

        onMounted(async() => {
    const modalHeader = document.body.querySelector('.modal-header');
    modalHeader.setAttribute('class', 'modal-header-no-drag');
    const menuData = await this.orm.read('ir.ui.menu', [this.props.Menu.id], ['groups_id']);
    this.state.group_ids = menuData[0].groups_id;
    if (this.selectionValuesRef.el) {
        const container = this.selectionValuesRef.el;

        // Destroy existing sortable if any
        const existingSortable = Sortable.get(container);
        if (existingSortable) existingSortable.destroy();

        Sortable.create(container, {
            animation: 150,
            ghostClass: 'sortable-ghost',

            onEnd: function(evt) {
                var elements = container.querySelectorAll('.SiblingMenu');
                elements.forEach(function(element, index) {
                    var Fields = element.attributes.value ? element.attributes.value.value : [null];
                    self.state.SiblingPosition[index] = Fields;
                });
            },
        });
    }
})
        useEffect((ev)=> {
            this.selected_parent(ev, this.state.ParentMenu)
        }, ()=> [this.state.ParentMenu])
    }
    selected_parent(ev, ParentMenus) {
        if (!ParentMenus) {
            this.props.isParent = "sibling"
        }
    }
    _onActionTypeChange(ev) {
    const value = ev.target.value;
    const actionType = value === '' ? false : value;

    this.state.ActionType = actionType;

    this.props.Menu.actionModel = actionType;

    // Clear action ID when action type is cleared
    if (!actionType) {
        this.state.actionID = false;
        this.props.Menu.actionID = false;
    }
}
/**
 * Deletes a child menu item after confirmation.
 * @param {number} menuId - The ID of the menu to delete
 */
async deleteMenu(menuId) {
    const self = this;
    // Show confirmation dialog
    this.dialogService.add(ConfirmationDialog, {
        title: _t("Delete Menu"),
        body: _t("Are you sure want to delete this menu item? This action cannot be undone."),
        confirm: async () => {
            try {
                const result = await this.rpc("/cyllo_studio/menuitem/delete", {
                    method: 'delete_menu',
                    menuId: menuId
                });

                if (result.success) {
                 this.notification.add({
                    title: _t("Deleted"),
                    message: "Deleted Menu",
                    description: "Successfully Deleted Menu",
                    type: "notification_panel",
                    notificationType: "success",
                });

                    // Remove the menu from childrenTree
                    if (this.props.Menu.childrenTree) {
                        const index = this.props.Menu.childrenTree.findIndex(m => m.id === menuId);
                        if (index !== -1) {
                            this.props.Menu.childrenTree.splice(index, 1);
                        }
                    }
                } else {
                    this.notification.add(_t("Failed to delete menu"), {
                        type: "danger",
                    });
                }
            } catch (error) {
                console.error("Error deleting menu:", error);
                this.notification.add(_t("An error occurred while deleting the menu"), {
                    type: "danger",
                });
            }
        },
        cancel: () => {}
    });
}
    async OnclickConfirmDialogue(ev){
        var MenuPosition = this.state.SiblingPosition
        if (Object.entries(MenuPosition).length <= 1) {
            var elements = document.querySelectorAll('.SiblingMenu');
            elements.forEach(function(element, index) {
                var Fields = element.attributes.value ? element.attributes.value.value : [null]
                MenuPosition[index] =  Fields;
            })
        }
        const result = await this.rpc("/cyllo_studio/move/childmenuitem", {
            method: 'move_child_menu',
            args: [],
            kwargs: {
                MenuName: document.querySelector('.MenuName').value,
                MenuPosition,
                ParentChange: this.state.ParentChange,
                Menu: this.props.Menu,
                ParentMenu: this.props.ParentMenu,
                groups: this.state.group_ids,
                ActiveMenu: this.state.ActiveMenu,
                ActionType: this.state.ActionType === '' ? false : this.state.ActionType,
                ActionModel: this.state.actionID || false,
                isCreate: this.props.isCreate
            }
        })
        this.props.close()
        this.action.doAction('studio_reload')
        window.location.reload()
    }
    addChild(ev, ParentMenu) {
        var data = this.dialogService.add(MenuCreationDialog, {
            isParent: "sibling",
            title: 'Menu Items Creation',
            ParentMenu: ParentMenu ? ParentMenu.id : this.menuService.getCurrentApp().id
        });
    }

    static template = "cyllo_studio.MenuConfigurationDialog";
    static props = {
        title: {
            validate: (m) => {
                return (
                    typeof m === "string" || (typeof m === "object" && typeof m.toString === "function")
                );
            },
            optional: true,
        },
        isParent: { type: String, optional: true },
        Menu: { type: Object, optional: true },
        menuName: { type: String, optional: true },
        ParentMenu: { type: Object, optional: true },
        ParentMenus: { type: Object, optional: true },
        Siblings: { type: Object, optional: true },
        close: { type: Function, optional: true}

    };
    static defaultProps = {
        title: "Menu Items Configuration"
    };
    static components = { Dialog, RecordSelector, MultiRecordSelector, CheckBox, CylloRecordSelector };

}

// new parent config
export class ParentMenuConfigurationDialog extends Component {
    async setup() {
        var self = this
        this.orm = useService("orm");
        this.action = useService("action");
        this.rpc = useService("rpc");
        this.menuService = useService("menu");
        this.inputRef = useRef("file-input");
        this.iconBoxRef = useRef('iconBox')
        this.inputRefButton = useRef("file-input-button");
        this.state = useState({
            group_ids: [],
            ActiveMenu: false,
            actionID: this.props.ParentMenu.actionID,
            ActionType: this.props.ParentMenu.actionModel,
            SiblingPosition: {},
            ParentChange: false,
            menuDetails: false,
            ChildParentMenu: false,
            Parents: [],
            iconVisible: false,
            iconSelectionVisible: false,
            iconToggle:false,
            uploadFile: false,

        })
        this.state.iconDefault = this.props.ParentMenu.webIconDataMimetype ? this.props.ParentMenu.webIconData : this.props.ParentMenu.webIcon

        onMounted(()=>{
            const modalHeader = document.body.querySelector('.modal-header');
            modalHeader.setAttribute('class', 'modal-header-no-drag');

            document.body.addEventListener('click', (el)=> {
                if(this.state.iconToggle && !this.iconBoxRef.el?.contains(el.target)){
                    this.state.iconToggle = false
                }
                if(el.target.parentElement.parentElement.id==='iconButton'||el.target.parentElement.id){
                    this.state.iconToggle = true
                }
            })
        })

        this.state.menuDetails = await this.orm.read('ir.ui.menu',
            [
                this.props.ParentMenu.id
            ]
            , ['id', 'name', 'groups_id', 'active'])
            this.state.group_ids = this.state.menuDetails[0].groups_id
            this.state.ActiveMenu = this.state.menuDetails[0].active

    }
    get IconClass(){
        return ICONCLASS
    }

    async AppIconUpload(ev) {
        const inputImage = this.inputRef.el
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
            reader.onload = async function(e) {
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
            reader.onload = async function(e) {
                const binaryData = e.target.result;
                const image = new Image();
                image.src = binaryData;
                self.state.IconImage = binaryData
                self.state.isImageUploaded = true;
            };
            reader.readAsDataURL(file_from_upload);
            this.state.uploadFile = true
        }
    }

    onClickKpiIcon(){
        this.state.iconVisible = !this.state.iconVisible;
        this.state.iconSelectionVisible = !this.state.iconSelectionVisible;
    }
    onCloseKpiIcon(){
        this.state.iconSelectionVisible = !this.state.iconSelectionVisible;
    }
    selectIcon(className){
         this.state.iconSelectionVisible = !this.state.iconSelectionVisible;
         this.state.iconDefault = className
         this.props.ParentMenu.webIconDataMimetype = ''
         this.state.IconImage = ""
         this.state.imageUrl = ''
         this.state.iconToggle = false
         this.state.uploadFile = true;
    }
    handleIconVisible(){
        this.state.iconToggle = true
    }
    async OnclickConfirmDialogueParentMenu(ev){
        let iconImage = ''
        if(this.state.iconDefault!==this.props.ParentMenu.webIcon){
            iconImage = this.state.iconDefault ? this.state.iconDefault : this.state.IconImage
        }
        if (this.state.uploadFile === true) {
            const result = await this.rpc("/cyllo_studio/parentmenuitem", {
                method: 'parent_menu',
                args: [],
                kwargs: {
                    MenuName: document.querySelector('.MenuName').value,
                    IconImage: iconImage,
                    ParentMenu: this.props.ParentMenu,
                    groups: this.state.group_ids,
                    ActiveMenu: this.state.ActiveMenu,
                    ActionType: this.state.ActionType,
                    ActionModel: this.state.actionID
                }
            })
        } else {
            const result = await this.rpc("/cyllo_studio/parentmenuitem", {
                method: 'parent_menu',
                args: [],
                kwargs: {
                    MenuName: document.querySelector('.MenuName').value,
                    ParentMenu: this.props.ParentMenu,
                    groups: this.state.group_ids,
                    ActiveMenu: this.state.ActiveMenu,
                    ActionType: this.state.ActionType,
                    ActionModel: this.state.actionID
                }
            })
        }
        this.props.close()
        this.action.doAction('reload')
    }
}
// Define the template and components for the ParentMenuConfigurationDialog component
ParentMenuConfigurationDialog.template = "cyllo_studio.ParentMenuConfigurationDialog";
ParentMenuConfigurationDialog.props = {
    isParent: { type: String, optional: true },
    title: {
        validate: (m) => {
            return (
                typeof m === "string" || (typeof m === "object" && typeof m.toString === "function")
            );
        },
        optional: true,
    },
    Menu: { type: Object, optional: true },
    menuName: { type: String, optional: true },
    ParentMenu: { type: Object, optional: true },
    ParentMenus: { type: Object, optional: true },
    Siblings: { type: Object, optional: true },
    close: { type: Function, optional: true}
};
ParentMenuConfigurationDialog.defaultProps = {
    title: ("Parent Menu Items Configuration"),
};
ParentMenuConfigurationDialog.components = { Dialog, MultiRecordSelector, RecordSelector, CheckBox, CylloRecordSelector };
