/** @odoo-module **/
import { WebClient } from "@web/webclient/webclient";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
patch(WebClient.prototype,{
    /**
     * Overrides the setup method of the WebClient prototype to customize the title
     * and set up the menu service.
     */
    async setup(){
        this.menuService=useService("menu");super.setup()
        // Replacing the tittle near favicon
        this.title.setParts({ zopenerp: 'Cyllo' });
    },
});