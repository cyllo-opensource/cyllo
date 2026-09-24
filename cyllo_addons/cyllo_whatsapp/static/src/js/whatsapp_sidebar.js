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
        useBus(this.env.bus, "on_Click_Configuration", () => this.showConfiguration())
        this.orm = useService('orm')
        this.actionService = useService("action");
        this.searchBox = useRef('search')
        this.userConfigModal = useRef('userConfigModal')
        this.configModal = useRef('configModal')
        this.account_uid = useRef('account_uid')
        this.user_email = useRef('user_email')
        this.user_name = useRef('user_name')
        this.app_uid = useRef('app_uid')
        this.phone_uid = useRef('phone_uid')
        this.token = useRef('token')
        this.dialog = useService("dialog");
        this.contact = useRef("contact");
        this.chat = useRef("chat");
        this.profileimagepicker = useRef('profileImagePicker')
        this.contactconatainer = useRef("contact-container");
        this.configurationcontainer = useRef("configuration-container");
        this.state = useState({
            partnerHistory: {},
            dropdown: false,
            user: {},
            configuration: false,
            appid: false,
            phone_number: false,
            business_account: false,
            access_token: false,
        })
        this.state.user = await this.orm.call("res.users", "get_user_data", [{}, session.uid])
    }

    showConfiguration() {
        this.contactconatainer.el.classList.add('d-none')
        this.configurationcontainer.el.classList.remove('d-none')
    }

    onClickCancel() {
        this.contactconatainer.el.classList.remove('d-none')
        this.configurationcontainer.el.classList.add('d-none')
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

    onClickSave() {
        this.dialog.add(ConfirmationDialog, {
            body: _t("Do you want to save the changes?"),
            confirmLabel: _t("Yes"),
            confirm: async () => {
                await this.orm.call("res.users", "action_update_data", [session.uid,
                    this.state.business_account, this.state.appid,
                    this.state.phone_number, this.state.access_token])
                window.location.reload();
            },
            cancel: () => {

            },
        });
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
        if (this.userConfigModal.el.classList.contains("d-none")) {
            this.userConfigModal.el.classList.remove("d-none")
        } else {
            this.userConfigModal.el.classList.add("d-none")
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

    async openConfig() {
        if (this.configModal.el.classList.contains("d-none")) {
            this.configModal.el.classList.remove("d-none")
        } else {
            this.configModal.el.classList.add("d-none")
        }
    }

    async updateConfig() {
        if (this.state.configuration) {
            if (this.account_uid.el.value === this.state.user['account_uid'] &&
                this.app_uid.el.value === this.state.user['app_uid'] &&
                this.phone_uid.el.value === this.state.user['phone_uid'] &&
                this.token.el.value === this.state.user['token']) {
                this.state.configuration = false
            } else {
                this.dialog.add(ConfirmationDialog, {
                    body: _t("Do you want to save the changes?"),
                    confirmLabel: _t("Yes"),
                    confirm: async () => {
                        await this.orm.call("res.users", "action_update_data", [session.uid,
                            this.account_uid.el.value, this.app_uid.el.value,
                            this.phone_uid.el.value, this.token.el.value])
                        window.location.reload();
                    },
                    cancel: () => {
                        window.location.reload();
                    },
                });
            }
        } else {
            this.state.configuration = true
        }
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