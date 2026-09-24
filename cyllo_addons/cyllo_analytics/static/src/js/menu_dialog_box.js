/** @odoo-module **/
import { Dialog } from "@web/core/dialog/dialog";
import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { Record } from "@web/model/record";
import { CharField } from "@web/views/fields/char/char_field";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { SelectMenu } from "@web/core/select_menu/select_menu";


export class MenuTreeNode extends Component {
    static template = "cyllo_analytics.MenuTreeNode";
    static components = { MenuTreeNode };

    onDragOver(ev) { this.props.comp.onDragOver(ev); }
    onDragLeave(ev) { this.props.comp.onDragLeave(ev); }
    onDrop(ev) { this.props.comp.onDrop(ev); }
    onDragOverInto(ev) { if (!this.props.node.isTemp) this.props.comp.onDragOverInto(ev); }
    onDragLeaveInto(ev) { if (!this.props.node.isTemp) this.props.comp.onDragLeaveInto(ev); }
    onDropInto(ev) { if (!this.props.node.isTemp) this.props.comp.onDropInto(ev); }
    onResetDrop(ev) { this.props.comp.resetDrop(ev); }
    onDragStartNewMenu(ev) { if (this.props.node.isTemp) this.props.comp.onDragStartNewMenu(ev); }
    onDragEndNewMenu(ev) { if (this.props.node.isTemp) this.props.comp.onDragEndNewMenu(ev); }
}
export class MenuDialog extends Component {
    setup() {
        this.orm = useService('orm')
        this.action = useService('action')
        this.menuService = useService("menu")
        this.notification = useService("notification")
        this.data = {};
        this.state = useState({
            apps: [],
            selectedAppId: "",
            selectedAppName: "",
            appTree: null,
            targetParentId: null,
            targetParentName: "",
            targetSequence: 0,
            isDropped: false,
            isDragging: false,
            isDropdownOpen: false,
        });
        onWillStart(async () => {
            await this.loadApps();
        });
    }
    async loadApps() {
        try {
            this.state.apps = await this.orm.call("dashboard.config", "get_app_menus", [null]);
        } catch (e) {
            this.notification.add('Failed to load apps.', { type: 'danger' });
        }
    }
    async onAppChange(ev) {
        const appId = ev.target.value;
        this.selectApp(appId);
    }
    async onAppChangeDropdown(appId, appName) {
        this.selectApp(appId, appName);
    }
    toggleAppDropdown() {
        this.state.isDropdownOpen = !this.state.isDropdownOpen;
    }
    onSelectApp(appId) {
        if (appId) {
            const app = this.state.apps.find(a => a.id === appId);
            this.selectApp(appId, app?.name || '');
        } else {
            this.selectApp('', '');
        }
    }
    get appChoices() {
        return this.state.apps.map(app => ({ value: app.id, label: app.name }));
    }
    async selectApp(appId, appName = "") {
        this.state.selectedAppId = appId;
        this.state.selectedAppName = appName || (this.state.apps.find(a => a.id == appId) || {}).name || "";
        this.state.appTree = null;
        this.state.targetParentId = null;
        this.state.targetParentName = "";
        this.state.isDropped = false;
        this.state.isDropdownOpen = false;
        if (appId) {
            try {
                this.state.appTree = await this.orm.call("dashboard.config", "get_app_menus", [parseInt(appId)]);
                // Default: place at TOP of the selected app's root menu
                let newSeq = 0;
                if (this.state.appTree.children && this.state.appTree.children.length > 0) {
                    newSeq = parseFloat(this.state.appTree.children[0].sequence) - 0.5;
                }
                this.state.targetParentId = this.state.appTree.id;
                this.state.targetParentName = this.state.appTree.name;
                this.state.targetSequence = Math.round(newSeq);
                this.state.isDropped = true;
                this.addTempNodeToTree(this.state.targetParentId, newSeq);
            } catch (e) {
                this.notification.add('Failed to load menu structure.', { type: 'danger' });
            }
        }
    }
    onDragStartNewMenu(ev) {
        ev.dataTransfer.effectAllowed = "move";
        this.state.isDragging = true;
        // --- Custom Drag Ghost Image (Smaller Size) ---
        const dragIcon = ev.currentTarget.cloneNode(true);
        dragIcon.style.position = "absolute";
        dragIcon.style.top = "-1000px";
        dragIcon.style.left = "-1000px";
        dragIcon.style.fontSize = "11px";
        dragIcon.style.padding = "4px 10px";
        dragIcon.style.opacity = "0.9";
        dragIcon.style.boxShadow = "none";
        document.body.appendChild(dragIcon);
        ev.dataTransfer.setDragImage(dragIcon, 10, 10);
        setTimeout(() => document.body.removeChild(dragIcon), 10);
        // Show drop zone indicators
        document.querySelectorAll('.drop-zone-indicator').forEach(el => {
            el.style.border = '2px dashed #dee2e6';
            el.style.height = '18px';
            el.style.margin = '4px 0';
        });
        document.querySelectorAll('.drop-into-zone').forEach(el => {
            el.style.border = '1px dashed #aabc14';
        });
    }
    onDragEndNewMenu(ev) {
        this.state.isDragging = false;
        document.querySelectorAll('.drop-zone-indicator').forEach(el => {
            el.style.border = 'none';
            el.style.backgroundColor = 'transparent';
            el.style.height = '0px';
            el.style.margin = '0';
        });
        document.querySelectorAll('.drop-into-zone').forEach(el => {
            el.style.backgroundColor = 'white';
            el.style.border = '1px solid #dee2e6';
        });
    }
    onDragOver(ev) {
        ev.preventDefault();
        ev.currentTarget.style.backgroundColor = '#f4f6e8';
        ev.currentTarget.style.border = '2px solid #aabc14';
        ev.currentTarget.style.height = '18px';
        ev.currentTarget.style.opacity = '1';
    }
    onDragLeave(ev) {
        ev.currentTarget.style.backgroundColor = 'transparent';
        ev.currentTarget.style.border = '2px dashed #dee2e6';
        ev.currentTarget.style.height = '14px';
        ev.currentTarget.style.opacity = '1';
    }
    addTempNodeToTree(parentId, sequence, beforeId = null, afterId = null) {
        if (!this.state.appTree) return;
        // 1. Remove existing temp node recursively
        const removeTemp = (node) => {
            if (node.children) {
                const idx = node.children.findIndex(c => c.id === 'temp_new_menu');
                if (idx !== -1) {
                    node.children.splice(idx, 1);
                    return true;
                }
                for (let child of node.children) {
                    if (removeTemp(child)) return true;
                }
            }
            return false;
        };
        removeTemp(this.state.appTree);
        // 2. Add new temp node
        const tempNode = {
            id: 'temp_new_menu',
            name: this.data.name || 'New Dashboard Menu',
            sequence: sequence,
            isTemp: true,
            children: []
        };
        const insertTemp = (node) => {
            if (node.id === parentId) {
                if (!node.children) node.children = [];
                if (beforeId) {
                    const idx = node.children.findIndex(c => c.id === parseInt(beforeId));
                    if (idx !== -1) {
                        node.children.splice(idx, 0, tempNode);
                        return true;
                    }
                } else if (afterId) {
                    const idx = node.children.findIndex(c => c.id === parseInt(afterId));
                    if (idx !== -1) {
                        node.children.splice(idx + 1, 0, tempNode);
                        return true;
                    }
                }
                // Fallback (e.g. drop into or app init)
                node.children.push(tempNode);
                node.children.sort((a, b) => a.sequence - b.sequence);
                return true;
            }
            if (node.children) {
                for (let child of node.children) {
                    if (insertTemp(child)) return true;
                }
            }
            return false;
        };
        insertTemp(this.state.appTree);
    }
    onDrop(ev) {
        ev.preventDefault();
        this.onDragLeave(ev); // reset styling
        const parentId = parseInt(ev.currentTarget.dataset.parentId);
        const beforeSeq = ev.currentTarget.dataset.beforeSeq;
        const afterSeq = ev.currentTarget.dataset.afterSeq;
        const beforeId = ev.currentTarget.dataset.beforeId;
        const afterId = ev.currentTarget.dataset.afterId;
        // Calculate sequence. Use a decimal to ensure it sorts EXACTLY between existing integer sequences
        let newSeq = 0;
        if (beforeSeq) {
            newSeq = parseFloat(beforeSeq) - 0.5;
        } else if (afterSeq) {
            newSeq = parseFloat(afterSeq) + 10;
        }
        this.state.targetParentId = parentId;
        this.state.targetSequence = Math.round(newSeq);
        this.state.targetBeforeId = beforeId ? parseInt(beforeId) : null;
        this.state.targetAfterId = afterId ? parseInt(afterId) : null;
        // Find parent name for display
        const findName = (node) => {
            if (node.id === parentId) return node.name;
            if (node.children) {
                for (let child of node.children) {
                    const found = findName(child);
                    if (found) return found;
                }
            }
            return null;
        };
        this.state.targetParentName = findName(this.state.appTree) || "Selected Menu";
        this.state.isDropped = true;
        this.addTempNodeToTree(parentId, newSeq, beforeId, afterId);
    }
    onDragOverInto(ev) {
        ev.preventDefault();
        ev.currentTarget.style.backgroundColor = '#f4f6e8';
        ev.currentTarget.style.border = '2px solid #aabc14';
    }
    onDragLeaveInto(ev) {
        ev.currentTarget.style.backgroundColor = 'white';
        ev.currentTarget.style.border = '1px solid #dee2e6';
    }
    onDropInto(ev) {
        ev.preventDefault();
        this.onDragLeaveInto(ev);
        const parentId = parseInt(ev.currentTarget.dataset.intoParentId);
        const parentName = ev.currentTarget.dataset.intoParentName;
        this.state.targetParentId = parentId;
        this.state.targetParentName = parentName;
        this.state.targetSequence = 999; // Append at the end of the chosen parent
        this.state.isDropped = true;
        this.addTempNodeToTree(parentId, 999);
        this.notification.add('Target set!', { type: 'success' });
    }
    resetDrop(ev) {
        if (ev) ev.stopPropagation();
        // Remove temp node recursively
        if (this.state.appTree) {
            const removeTemp = (node) => {
                if (node.children) {
                    const idx = node.children.findIndex(c => c.id === 'temp_new_menu');
                    if (idx !== -1) {
                        node.children.splice(idx, 1);
                        return true;
                    }
                    for (let child of node.children) {
                        if (removeTemp(child)) return true;
                    }
                }
                return false;
            };
            removeTemp(this.state.appTree);
        }
        this.state.targetParentId = null;
        this.state.targetParentName = "";
        this.state.targetSequence = 0;
        this.state.targetBeforeId = null;
        this.state.targetAfterId = null;
        this.state.isDropped = false;
    }
    onNameInput(ev) {
        this.updateTempNodeName(ev.target.value);
    }
    updateTempNodeName(name) {
        if (!this.state.appTree) return;
        const findTemp = (node) => {
            if (node.id === 'temp_new_menu') {
                node.name = name || 'New Dashboard Menu';
                return true;
            }
            if (node.children) {
                for (const child of node.children) {
                    if (findTemp(child)) return true;
                }
            }
            return false;
        };
        findTemp(this.state.appTree);
    }
    get recordProps() {
        var name = { type: "char", string: "Name" }
        var fields = { name }
        return {
            mode: "edit",
            onRecordChanged: (record, changes) => {
                for (var key in changes) {
                    this.data[key] = changes[key]
                }
                if ('name' in changes) {
                    this.updateTempNodeName(changes.name);
                }
            },
            resModel: "dashboard.config.menu",
            resId: this.id,
            fieldNames: fields,
            activeFields: fields,
        };
    }
    async handleConfirm() {
        if (!this.data.name) {
            this.notification.add('Please provide a name', { type: 'danger' })
            return
        }
        if (!this.state.targetParentId) {
            this.notification.add('Please select a parent menu by dragging the item.', { type: 'danger' })
            return
        }
        const action = await this.createAction();
        const menuData = {
            name: this.data.name,
            parent_id: this.state.targetParentId,
            action: `ir.actions.client,${action}`,
            is_cyllo_analytic_menu: true,
            sequence: this.state.targetSequence,
        };
        const newMenuId = await this.orm.call("dashboard.config", "create_menu_with_sequence", [
            menuData,
            this.state.targetBeforeId,
            this.state.targetAfterId
        ]);
        await this.orm.call("dashboard.config", "append_menu", [this.props.rec_id, newMenuId]);
        this._cancel();
        this.action.doAction("reload_context")
    }
    async createAction() {
        const actionData = [{
            name: this.props.name,
            tag: 'cy_analytic_dashboard',
            target: 'current',
            context: {
                rec_id: this.props.rec_id,
                is_subAction: true,
            }
        }]
        const action = await this.orm.create('ir.actions.client', actionData)
        return action
    }
    async _cancel() {
        this.props.close();
    }
}
// Define the template for the MenuDialog component
MenuDialog.template = "cyllo_analytics.MenuDialog"
MenuDialog.components = { Dialog, Record, CharField, MenuTreeNode, Dropdown, DropdownItem, SelectMenu };