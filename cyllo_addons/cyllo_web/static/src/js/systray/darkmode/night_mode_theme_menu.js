/** @odoo-module **/
import { Component, onMounted, useRef, onWillStart, useState } from '@odoo/owl';
import { registry } from '@web/core/registry';
import { useService } from "@web/core/utils/hooks";

/**
 * Menu item appended in the systray part of the navbar
*/
export class NightModeTheme extends Component {
    setup() {
        this.env.bus.addEventListener("TOGGLE_DARK_MODE", async () => {
            await this.onToggleClick()
        })
        this.orm = useService('orm')
        this.state = useState({ checked: false })
        this.root = useRef('root')
        this.refs = useRef('iconContainer')
        this.backend = ''
        this.ui = useService("ui");
        this.block = () => this.ui.block();
        this.unblock = () => this.ui.unblock();
        this.darkReader = false
        onWillStart(async () =>
            this.state.checked = await this.orm.call('res.users', 'get_active', [])
        )
        onMounted(() => {
            this.root.el.querySelector('#cy_check').checked = this.state.checked;

            if (this.state.checked) {
                DarkReader.enable();
                this.updateIcons(true);
            } else {
                this.updateIcons(false);
            }

            this.env.bus.addEventListener("DARK_MODE_UPDATED", (event) => {
                this.state.checked = event.detail;
                this.updateIcons(event.detail);
            });
        });

    }


    getSunIcon() {
        return `
             <i class="ri-sun-line cy-icons cy-stray-icon-sp"></i>
        `;
    }

    getMoonIcon() {
        return `
           <i class="ri-moon-line cy-icons cy-stray-icon-sp"></i>
        `;
    }

    updateIcons(isDark) {
        const icon1 = this.refs.el;
        const iconHtml = isDark ? this.getSunIcon() : this.getMoonIcon();
        if (icon1) icon1.innerHTML = iconHtml;
    }

    /**
     * Handle the click event when toggling night mode.
     * @param {Event} event - The click event.
     */
    async onToggleClick() {
        this.ui.block();
        try {
            this.state.checked = !this.state.checked;

            const backend = await this.orm.call('res.users', 'toggle_night_mode', [this.state.checked]);
            localStorage.setItem('darkMode', this.state.checked);

            if (backend) {
                this.backend = 'true';
                DarkReader.enable();
            } else {
                this.backend = 'false';
                DarkReader.disable();
            }

            this.env.bus.trigger('DARK_MODE_UPDATED', this.state.checked);
            this.updateIcons(this.state.checked);
        } finally {
            this.ui.unblock();
        }
    }


}

NightModeTheme.template = 'NightModeTheme';
export const NightModeSystrayItem = {
    Component: NightModeTheme,
};

registry.category("systray").add("NightModeTheme", NightModeSystrayItem, { sequence: 0 });