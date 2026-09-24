/** @odoo-module **/
/* Add new class SwitchLanguageMenu on systray */
import {Dropdown} from '@web/core/dropdown/dropdown';
import {DropdownItem} from '@web/core/dropdown/dropdown_item';
import {useService} from '@web/core/utils/hooks';
import {registry} from '@web/core/registry';
import {Component, onWillStart} from '@odoo/owl';
import {jsonrpc} from "@web/core/network/rpc_service";
import {session} from '@web/session';

/* Export new class SwitchLanguageMenu by extending Components */
export class SwitchLanguageMenu extends Component {
    setup() {
        this.ormService = useService('orm');
        this.action = useService("action");
        this.userLang = session.bundle_params.lang;
        onWillStart(async () => {
            /* Get all active languages, code and flag images */
            this.langs = await this.ormService.searchRead('res.lang', [], ['name', 'code', 'flag_image']);
            this.lang = this.langs.find(({code}) => code == this.userLang)
        })
    }

    get selectedLanguage() {
        return this.lang.code.split('_')[0].toUpperCase();
    }

    /* switching function of language
    * @params: lang(object) containing object of res lang model*/
    async switchLanguage(lang) {
        if (this.lang === lang) {
            return
        }
        /* when changing language, current language of user will change  */
        await jsonrpc('/lang_switch', {
            lang: lang.code
        })
        this.action.doAction('reload_context');
    }
}

SwitchLanguageMenu.template = 'cyllo_web.SwitchLanguageMenu';
SwitchLanguageMenu.components = {Dropdown, DropdownItem};
export const languageSystrayItem = {
    Component: SwitchLanguageMenu,
    isDisplayed: (_) => {
        return session.lang_count > 1;
    }
};
registry.category('systray').add('SwitchLanguageMenu', languageSystrayItem, {sequence: 1});