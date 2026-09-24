/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, useSubEnv } from "@odoo/owl";
import { StickyNotes } from "./sticky_note";

export class StickyNotesSystray extends Component {
    /**
     * @extends Component
     */
    setup() {
        this.dialogService = useService("dialog")
        super.setup(...arguments);
        this.state = useState({
            isOpen: false
        })
        useSubEnv({
            noteClose: this.close_note.bind(this)
        });
    }

    async sticky_note(ev) {
        //Toggles the visibility of a sticky note and applies a overlay effect
        this.state.isOpen = !this.state.isOpen
        var inputGroup = this.__owl__.bdom.parentEl.ownerDocument.querySelector('.input-group')
        var topNavBar = this.__owl__.bdom.parentEl.ownerDocument.querySelector('.cy-top-navbar')
        var btnOutSec = this.__owl__.bdom.parentEl.ownerDocument.querySelector('.btn-outline-secondary')
        var mailChatter = this.__owl__.bdom.parentEl.ownerDocument.querySelector('.o-mail-Chatter-top')
        var TimeOff = this.__owl__.bdom.parentEl.ownerDocument.querySelector('.o_timeoff_dashboard')
        var listGroupItem = this.__owl__.bdom.parentEl.ownerDocument.querySelector('.list-group-item')
        var chartContainers = this.__owl__.bdom.parentEl.ownerDocument.querySelectorAll('.o-chart-container')
        var scrollBars = this.__owl__.bdom.parentEl.ownerDocument.querySelectorAll('.o-scrollbar')
        var groupItems = this.__owl__.bdom.parentEl.ownerDocument.querySelectorAll('.o_kanban_view .o_search_panel_section .list-group-item.active')

        if (this.state.isOpen) {
            /**
            * Check if the note is open
            */
            this.__owl__.bdom.parentEl.ownerDocument.querySelector('.o_web_client').classList.add('overlay');
            this.__owl__.bdom.parentEl.ownerDocument.querySelector('.o_main_navbar').classList.add('overlay');
            if (inputGroup) {
                inputGroup.style.borderBottom = '1px solid #696969';
            }
            if (topNavBar) {
                topNavBar.style.borderBottom = '1px solid #696969';
            }
            if (btnOutSec){
                btnOutSec.style.borderColor = '#696969';
            }
            if (mailChatter){
                mailChatter.classList.add('overlay');
            }
            if (TimeOff){
                TimeOff.classList.add('overlay');
            }
            if (listGroupItem){
                listGroupItem.style.backgroundColor = 'transparent';
            }
            groupItems.forEach(function(groupItem){
                groupItem.classList.add('overlay');
            })
            chartContainers.forEach(function(chartContainer) {
                chartContainer.classList.add('overlay');
            });
            scrollBars.forEach(function(scrollBar) {
                scrollBar.classList.add('overlay');
            })
        } else {
            this.__owl__.bdom.parentEl.ownerDocument.querySelector('.o_web_client').classList.remove('overlay');
            this.__owl__.bdom.parentEl.ownerDocument.querySelector('.o_main_navbar').classList.remove('overlay');
            if (inputGroup) {
                inputGroup.style.borderBottom = '';
            }
            if (topNavBar) {
                topNavBar.style.borderBottom = '';
            }
            if (btnOutSec){
                btnOutSec.style.borderColor = '';
            }
            if (mailChatter){
                mailChatter.classList.remove('overlay');
            }
            groupItems.forEach(function(groupItem){
                groupItem.classList.remove('overlay');
            });
            if (TimeOff){
                TimeOff.classList.remove('overlay');
            }
            if (listGroupItem){
                listGroupItem.style.backgroundColor = '';
            }
            chartContainers.forEach(function(chartContainer) {
                chartContainer.classList.remove('overlay');
            });
            scrollBars.forEach(function(scrollBar) {
                scrollBar.classList.remove('overlay');
            })
        }
    }

    close_note() {
        /**
        * When a note is open, it will overlay the views. When the note is closed, the overlay
        effect is removed from the elements.
        */
        var inputGroup = this.__owl__.bdom.parentEl.ownerDocument.querySelector('.input-group')
        var topNavBar = this.__owl__.bdom.parentEl.ownerDocument.querySelector('.cy-top-navbar')
        var btnOutSec = this.__owl__.bdom.parentEl.ownerDocument.querySelector('.btn-outline-secondary')
        var mailChatter = this.__owl__.bdom.parentEl.ownerDocument.querySelector('.o-mail-Chatter-top')
        var TimeOff = this.__owl__.bdom.parentEl.ownerDocument.querySelector('.o_timeoff_dashboard')
        var listGroupItem = this.__owl__.bdom.parentEl.ownerDocument.querySelector('.list-group-item')
        var chartContainers = this.__owl__.bdom.parentEl.ownerDocument.querySelectorAll('.o-chart-container')
        var scrollBars = this.__owl__.bdom.parentEl.ownerDocument.querySelectorAll('.o-scrollbar')
        var groupItems = this.__owl__.bdom.parentEl.ownerDocument.querySelectorAll('.o_kanban_view .o_search_panel_section .list-group-item.active')
        this.state.isOpen = false
        if (this.state.isOpen) {
            /**
            * Check if the note is open
            */
            this.__owl__.bdom.parentEl.ownerDocument.querySelector('.o_web_client').classList.add('overlay');
            this.__owl__.bdom.parentEl.ownerDocument.querySelector('.o_main_navbar').classList.add('overlay');
            if (inputGroup) {
                inputGroup.style.borderBottom = '1px solid #696969';
            }
            if (topNavBar) {
                topNavBar.style.borderBottom = '1px solid #696969';
            }
            if (btnOutSec){
                btnOutSec.style.borderColor = '#696969';
            }
            if (mailChatter){
                mailChatter.classList.add('overlay');
            }
            if (TimeOff){
                TimeOff.classList.add('overlay');
            }
            if (listGroupItem){
                listGroupItem.style.backgroundColor = 'transparent';
            }
            groupItems.forEach(function(groupItem) {
                groupItem.classList.add('overlay');
            });
            chartContainers.forEach(function(chartContainer) {
                chartContainer.classList.add('overlay');
            });
            scrollBars.forEach(function(scrollBar) {
                scrollBar.classList.add('overlay');
            })
        } else {
            this.__owl__.bdom.parentEl.ownerDocument.querySelector('.o_web_client').classList.remove('overlay');
            this.__owl__.bdom.parentEl.ownerDocument.querySelector('.o_main_navbar').classList.remove('overlay');
            if (inputGroup) {
                inputGroup.style.borderBottom = '';
            }
            if (topNavBar) {
                topNavBar.style.borderBottom = '';
            }
            if (btnOutSec){
                btnOutSec.style.borderColor = '';
            }
            if (mailChatter){
                mailChatter.classList.remove('overlay');
            }
            if (TimeOff){
                TimeOff.classList.remove('overlay');
            }
            if (listGroupItem){
                listGroupItem.style.backgroundColor = '';
            }
            groupItems.forEach(function(groupItem) {
                groupItem.classList.remove('overlay');
            });
            chartContainers.forEach(function(chartContainer) {
                chartContainer.classList.remove('overlay');
            });
            scrollBars.forEach(function(scrollBar) {
                scrollBar.classList.remove('overlay');
            })
        }
    }
}

StickyNotesSystray.template = "StickyNotesSystray";
StickyNotesSystray.props = {
    nameShow: { type: Boolean, optional: true },
};
export const systrayItem = {
    Component: StickyNotesSystray,
};
StickyNotesSystray.components = {StickyNotes}
registry.category("systray").add("StickyNotesSystray", systrayItem, {sequence: 1000});