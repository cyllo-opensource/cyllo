/** @odoo-module **/

import { Component } from "@odoo/owl";

/**
 * Shared markup for a cog-menu button: <li><a class="... cy-navitem-list
 * ..."><icon slot><text slot></a></li>, matching the classes every existing
 * item (Refresh, Split View, Add to Shortcuts, Export All) already hand-rolls
 * — see cyllo_base/COG_MENU.md.
 *
 * Direct-action usage (matches the existing cogMenuRegistry.add(...) pattern):
 *   <CogMenuItem onClick.bind="onMyAction" accesskey="X">
 *       <t t-set-slot="icon"><i class="ri-star-line"/></t>
 *       <t t-set-slot="text">My Action</t>
 *   </CogMenuItem>
 * Omit the `icon` slot entirely for a text-only item.
 *
 * Dropdown usage (e.g. the row's "Print" button, cog_menu_form.xml): pass a
 * `dropdown` slot instead of/as well as `onClick` — the item becomes a
 * Bootstrap dropdown toggle, and `onClick` is not called (Bootstrap's own
 * data-bs-toggle handles opening it):
 *   <CogMenuItem accesskey="P">
 *       <t t-set-slot="icon"><i class="ri-printer-line"/></t>
 *       <t t-set-slot="text">Print</t>
 *       <t t-set-slot="dropdown">
 *           <li t-on-click="() => doThing(x)"><a class="dropdown-item">X</a></li>
 *       </t>
 *   </CogMenuItem>
 */
export class CogMenuItem extends Component {
    // Forwards the native click event — Split View's handler reads
    // ev.target to figure out exactly what was clicked (icon vs label) for
    // its DOM toggling, so this can't be dropped even though most items
    // ignore the argument.
    onClick(ev) {
        this.props.onClick?.(ev);
    }
}
CogMenuItem.template = "cyllo_web.CogMenuItem";
CogMenuItem.props = {
    onClick: { type: Function, optional: true },
    accesskey: { type: String, optional: true },
    class: { type: String, optional: true },
    slots: { type: Object, optional: true },
};
