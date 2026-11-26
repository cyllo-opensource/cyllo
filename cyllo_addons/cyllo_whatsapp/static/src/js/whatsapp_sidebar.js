/** @odoo-module **/
const {Component} = owl;
import {useState, useRef} from "@odoo/owl";
import {useService, useBus} from "@web/core/utils/hooks";
import {WhatsappPartnerProfile} from './whatsapp_partner_profile'
import {Dropdown} from '@web/core/dropdown/dropdown';
import {DropdownItem} from '@web/core/dropdown/dropdown_item';
import {session} from "@web/session";
import {ConfirmationDialog} from "@web/core/confirmation_dialog/confirmation_dialog";
import {_t} from "@web/core/l10n/translation";


export class WhatsappSidebar extends Component {
    /* This function appears to initialize various properties and set up
    event listeners. */
    async setup() {
        useBus(this.env.bus, "on_Click_Configuration", () => this.openConfig())
        this.orm = useService('orm')
        this.actionService = useService("action")
        this.dialog = useService("dialog")
        this.searchBox = useRef('search')
        this.userConfigModal = useRef('userConfigModal')
        this.user_email = useRef('user_email')
        this.user_name = useRef('user_name')
        this.contact = useRef("contact")
        this.chat = useRef("chat")
        this.profileimagepicker = useRef('profileImagePicker')
        this.state = useState({
            partnerHistory: {},
            dropdown: false,
            user: {},
        })
        this.state.user = await this.orm.call("res.users", "get_user_data", [{}, session.uid])
    }

    /**
     * Opens the 'whatsapp.account.config' wizard. When the dialog is
     * closed, the user data is refreshed (and the other components are
     * notified) in case the user saved the configuration.
     */
    async openConfig() {
        await this.actionService.doAction({
            name: _t('Whatsapp Account Configuration'),
            res_model: 'whatsapp.account.config',
            type: 'ir.actions.act_window',
            views: [[false, 'form']],
            target: 'new',
        })
        this.state.user = await this.orm.call(
            "res.users", "get_user_data", [{}, session.uid])
        this.env.bus.trigger('WA_CONFIG_UPDATED')
    }

    onClickProfilePicture() {
        this.profileimagepicker.el.click()
    }

    onImageSelected(ev) {
        const file = ev.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = (e) => {
                this.orm.call("res.users", "change_profile_picture", [session.uid, e.target.result]).then(() => {
                    window.location.reload()
                });
            };
            reader.readAsDataURL(file);
        }
    }

    /* Quick search button function to visible global search area */

    /*
    Keyup function of search area to show partners as dropdown based
    on search
    */
    async onKeyUpSearch(ev) {
        this.state.partnerHistory = await this.orm.searchRead(
            "res.partner",
            [
                ["name", "ilike", this.searchBox.el.value],
                ["whatsapp_number", "!=", null],
            ],
            ['name']
        );
        this.state.dropdown = true
    }

    onSelectPartner(partner) {
        this.searchBox.el.value = ""
        this.state.dropdown = false
        this.env.bus.trigger('SEARCH_PARTNER', {partner: partner})
    }

    async switchTab(tab) {
        if (tab == 'chat') {
            this.contact.el.classList.add('d-none')
            this.chat.el.classList.remove('d-none')
        } else {
            this.chat.el.classList.add('d-none')
            this.contact.el.classList.remove('d-none')
            this.state.partnerHistory = await this.orm.searchRead(
                "res.partner",
                [
                    ["whatsapp_number", "!=", null],
                ],
                ['name']
            );
        }
    }

    async getUserProfile() {
        const isOpening = this.userConfigModal.el.classList.contains("d-none");
        const sidebar = this.userConfigModal.el.closest(".chatbox-left");
        if (isOpening) {
            this.userConfigModal.el.classList.remove("d-none")
            sidebar?.classList.add("cy-wa-profile-modal-open");
        } else {
            this.userConfigModal.el.classList.add("d-none")
            sidebar?.classList.remove("cy-wa-profile-modal-open");
        }
    }

    async getTemplate() {
        await this.actionService.doAction({
            name: 'Whatsapp Template',
            res_model: "whatsapp.template",
            views: [[false, "tree"]],
            type: "ir.actions.act_window",
            view_mode: "tree",
            target: "current",
        });
    }

    async updateUserConfig() {
        if (this.user_email.el.value === this.state.user['user_email'] &&
            this.user_name.el.value === this.state.user['name']) {
            this.getUserProfile()
        } else {
            this.dialog.add(ConfirmationDialog, {
                body: _t("Do you want to save the changes?"),
                confirmLabel: _t("Yes"),
                confirm: async () => {
                    await this.orm.call("res.users", "action_update_profile_data", [session.uid,
                        this.user_email.el.value, this.user_name.el.value])
                    window.location.reload();
                },
                cancel: () => {
                    window.location.reload();
                },
            });
        }
    }
}

/* Associate 'WhatsappSidebar' template with the WhatsappSidebar component.*/
WhatsappSidebar.template = 'WhatsappSidebar';
WhatsappSidebar.components = {
    WhatsappPartnerProfile,
    Dropdown,
    DropdownItem,
}
