/** @odoo-module **/
import { Component } from "@odoo/owl";
import { Dropdown } from '@web/core/dropdown/dropdown';
import { DropdownItem } from '@web/core/dropdown/dropdown_item';

/* Create new WhatsappChatTop by extending Component */
export class WhatsappChatTop extends Component {}

/* Associate 'WhatsappChatTop' template with the WhatsappChatTop component.*/
WhatsappChatTop.template = 'WhatsappChatTop';
WhatsappChatTop.components = {
    Dropdown,
    DropdownItem,
}