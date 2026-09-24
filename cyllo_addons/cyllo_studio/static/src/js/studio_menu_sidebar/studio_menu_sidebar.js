/** @odoo-module **/
import { useService } from "@web/core/utils/hooks";
const {
    useState,
    useEffect,
    useRef,
    onMounted
} = owl;

import {
    ParentMenuConfigurationDialog,
    MenuCreationDialog,
    MenuConfigurationDialog
} from "@cyllo_studio/js/studio_menu_sidebar/dialog/dialog";

import { MenuSideBar } from "@cyllo_studio/js/studio_menu_sidebar/menu_sidebar";
import { FirstPage } from '@cyllo_studio/js/new_app/new_app_templates';

/**
 * Custom Studio Menu Sidebar Component
 * Extends the base MenuSideBar to provide drag-and-drop,
 * menu creation, menu configuration, and parent-child menu handling.
 */

export class StudioMenuSideBar extends MenuSideBar {
    static template = 'cyllo_studio.StudioMenuSideBar';
    setup() {
        super.setup();
        var self = this
        this.dialogService = useService("dialog")
        this.menuDragRef = useRef("MenuDragRef");
        this.cySubMenuDragRef = useRef("CySubMenuDragRef");
        this.menuService = useService("menu");
        this.orm = useService('orm');
        this.state = useState({
            ...this.state,
            MenuActive: false,
            MenuDraggable: false,
            CustomMenuDraggable: false,
        })
        onMounted(() => {
            this.MegaMenuDrag()
            this.state.MenuDraggable = true
        })
        useEffect(() => {
            if (this.state.MenuDraggable) {
                this.MenuDrag()
                this.state.MenuDraggable = false
            }
        }, () => [this.state.MenuDraggable, this.state.CustomMenuDraggable])
    }
    /**
     * Open the Cyllo Studio app creation dialog (stays in studio mode).
     */
    createApp() {
        this.dialogService.add(FirstPage, {
            title: 'Cyllo Studio',
        });
    }

    /**
     * Creates a SortableJS instance for drag-and-drop menus
     * @param {HTMLElement} el - The container element for draggable menus
     */
    createDragulaConfig(el) {
        const existingSortable = Sortable.get(el);
        if (existingSortable) existingSortable.destroy();
        return Sortable.create(el, {
            animation: 150,
            ghostClass: 'sortable-ghost',
            handle: '.ri-drag-move-line',
            onMove: function (evt) {
                if (
                    evt.dragged.classList.contains('cy-SubMenuDrag') &&
                    (evt.related?.classList.contains('cy-ParentMenuDrag') || !evt.related)
                ) {
                    return false;
                }

                if (evt.related) {
                    // Prevent dropping over the static Module Name header
                    if (evt.related.classList.contains('cy-sidebar-heading') || (evt.related.querySelector && evt.related.querySelector('.cy-sidebar-heading'))) {
                        return false;
                    }
                    // Prevent dropping below or over sticky action buttons (like Add Menu / New App)
                    if (evt.related.classList.contains('prevent-drag')) {
                        return false;
                    }
                }

                return true;
            },

            onEnd: async function (evt) {
                const elements = el.querySelectorAll('.menu-draggable');
                const MenuPosition = {};
                elements.forEach((element, index) => {
                    if (!element.classList.contains('prevent-drag') && element.hasChildNodes()) {
                        const Fields = element.attributes.menu_id ? element.attributes.menu_id.value : [null];
                        MenuPosition[index] = Fields;
                    }
                });
                await this.rpc("/cyllo_studio/move/menuitem", {
                    method: 'move_menu',
                    args: [],
                    kwargs: {
                        MenuPosition
                    },
                });
                this.action.doAction("studio_reload");
            }.bind(this),
        });
    }

    /**
     * Initializes drag for main (mega) menus.
     */
    MegaMenuDrag() {
        const MenuEl = this.menuDragRef.el;
        this.createDragulaConfig(MenuEl);
    }

    /**
    * Initializes drag for submenus.
    */
    MenuDrag() {
        const SubMenuEl = this.cySubMenuDragRef.el;
        this.createDragulaConfig(SubMenuEl);
    }


    /**
     * Opens the correct dialog for configuring parent or child menus
     * @param {Object} ParentMenu - The menu object being configured
     */
    ParentMenuCust(e, ParentMenu) {
        if (ParentMenu.id != ParentMenu.appID) {
            this.dialogService.add(MenuConfigurationDialog, {
                isParent: "children",
                title: 'Menu Items Configuration',
                Menu: ParentMenu,
                menuName: ParentMenu.name,
                ParentMenu: ParentMenu,
                ParentMenus: this.state.menus,
            });
        } else {
            this.dialogService.add(ParentMenuConfigurationDialog, {
                title: 'Parent Menu Items Configuration',
                menuName: ParentMenu.name,
                ParentMenus: this.state.menus,
                ParentMenu: ParentMenu,
            });
        }
    }
    /**
    * Opens a context menu for a menu item
    */
    studioOpenContextMenu() {
        event.preventDefault();
        var activeContextMenu = this.cyLeftSidebar.el.querySelectorAll('.studio-context-menu[style="display: flex;"]')
        activeContextMenu.forEach((menu) => {
            menu.style.display = 'flex'
        })
        const element = event.target.closest('.draggableDiv') || event.target.parentNode;
        var cyLeftSidebarContextMenu = element?.querySelector('.studio-context-menu')
        if (cyLeftSidebarContextMenu) {
            cyLeftSidebarContextMenu.style.display = 'flex';
            const hideContextMenu = () => {
                cyLeftSidebarContextMenu.style.display = 'flex';
                document.removeEventListener('click', hideContextMenu);
            };
            document.addEventListener('click', hideContextMenu);
        }
    }
    /**
    * Opens the dialog to create a new child menu
    * @param {Object} ParentMenu - Parent menu object
    * @param {Boolean} isCreate - Flag for creation mode
    */
    itemOnClick(ParentMenu, isCreate = false) {
        if (!ParentMenu && !this.menuService.getCurrentApp()?.id) {
            return this.notification.add({
                title: "Validation Error",
                message: "Unable to complete the process.",
                description: "You can't add menu to this model",
                type: "notification_panel",
                notificationType: "warning",
            });
        }
        this.dialogService.add(MenuCreationDialog, {
            isParent: "sibling",
            title: 'Menu Items Creation',
            ParentMenu: ParentMenu ? ParentMenu.id : this.menuService.getCurrentApp()?.id ?? false,
            isCreate
        });
        this.stateParentMenu = ParentMenu ? ParentMenu.id : this.menuService.getCurrentApp()?.id ?? false
    }

    /**
     * Opens the dialog to configure a child menu item
     */
    ChildMenuCust(ch_menu, ParentMenu, menuChildren) {
        this.dialogService.add(MenuConfigurationDialog, {
            isParent: "sibling",
            title: 'Menu Items Configuration',
            Menu: ch_menu,
            menuName: ch_menu.name,
            ParentMenu: ParentMenu,
            ParentMenus: this.state.menus,
        });
    }

    /**
     * Handles clicking a menu item in the sidebar.
     * Applies restrictions on editable menus and highlights selected menu.
     */
    async onClickMenu(id, isApp, name = false) {
        if (id) {
            const menu = this.menuService.getMenuAsTree(id);
            const ActionDetails = menu.actionModel && menu.actionID ? await this.orm.read(menu.actionModel, [menu.actionID], []) : [];

            const restrictedMenuXmlIds = new Set([
                "base.menu_administration",
                "base.menu_management",
                "website.menu_website_configuration",
                "cyllo_workflow_automation.menu_work_auto_list",
                'cyllo_planning.menu_cyllo_planning_root',
                'cyllo_analytics.menu_cyllo_analytics_root',
                'cyllo_analytics.menu_sheets',
                'cyllo_analytics.menu_dashboard',
                'cyllo_analytics.menu_templates',
                'cyllo_sign.menu_cyllo_sign_root',
                'cyllo_documents.menu_cyllo_documents_root'
            ]);
            const restrictedModels = new Set(["res.config.settings", "ir.module.module",'work.auto']);

            let isRestricted = false;
            if (restrictedMenuXmlIds.has(menu.xmlid)) {
                isRestricted = true;
            }
            else if (isApp) {
                isRestricted = restrictedMenuXmlIds.has(menu.xmlid) ||
                    (ActionDetails.length && ActionDetails[0].res_model === "res.config.settings") ||
                    (ActionDetails.length && restrictedModels.has(ActionDetails[0].res_model));
            }
            else if (menu.actionModel === 'ir.actions.act_window') {
                const action_and_model = await this.rpc("cyllo_studio/_auto_models/actions", {
                    menuActionId: menu.actionID,
                });
                isRestricted = action_and_model && (
                    restrictedModels.has(action_and_model[0]) ||
                    action_and_model[3] === true ||
                    action_and_model[2] === true ||
                    (ActionDetails.length && ActionDetails[0].target === "new") ||
                    (ActionDetails.length && ActionDetails[0].res_model === "res.config.settings")
                );
            }
            else if (menu.actionModel === 'ir.actions.server') {
                isRestricted = true;
            }

            if (isRestricted) {
                return this.env.services.notification.add(
                    ("This action is not editable!"), {
                    type: 'danger',
                    title: ('Restricted')
                });
            } else {
                const menuId = `#main_menu${id}`;
                if (this.cyLeftSidebar.el.querySelector(menuId)) {
                    this.cyLeftSidebar.el.querySelectorAll('.cy_active_menu').forEach(menu => menu.classList.remove('cy_active_menu'));
                    this.cyLeftSidebar.el.querySelector(menuId)?.classList.add('cy_active_menu');
                }
            }
        }

        super.onClickMenu(id, isApp, name);

        let menu = this.menuService.getMenuAsTree(id);
        if (!menu.actionID) {
            menu = await this.getMenuWithAction(menu) || menu;
        }
        this.menuService.selectMenu(menu);
    }

    /**
     * Recursively searches for a menu with a defined action
     * @param {Object} menu - Menu tree object
     * @returns {Object|undefined} - Menu with action or undefined
     */
    async getMenuWithAction(menu) {
        if (menu.childrenTree) {
            for (const child of menu.childrenTree) {
                if (child.actionID || (child.children.length > 0 && await this.getMenuWithAction(child))) {
                    return child.actionID ? child : await this.getMenuWithAction(child);
                }
            }
        }
    }
}
