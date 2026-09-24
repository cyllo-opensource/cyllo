/** @odoo-module **/
import {
    StudioMenuSideBar
} from "@cyllo_studio/js/studio_menu_sidebar/studio_menu_sidebar";
import {
    patch
} from '@web/core/utils/patch';
import {
    useService
} from "@web/core/utils/hooks";
import { FirstPage } from '@cyllo_studio/js/new_app/new_app_templates';
import { onWillUpdateProps } from "@odoo/owl";


patch(StudioMenuSideBar.prototype, {
    setup() {
        super.setup();
        this.dialogService = useService("dialog");
        onWillUpdateProps(async (nextProps) => {
            const hashParams = new URLSearchParams(window.location.hash.slice(1));
            const actionId = hashParams.get('action');
        });
    },

    createApp() {
        this.dialogService.add(FirstPage, {
            title: 'Cyllo Studio',
        });
    },

    handleClose() {
        const currentUrl = this.action.currentController.action.tag === "PromptDialog" ?
            new URL(localStorage.getItem('ExistingStudioPage')?.split(",")[0] || window.location.href) :
            localStorage.getItem('X2ManysStudioPage')?.split(",")[1] ?
            new URL(localStorage.getItem('X2ManysStudioPage').split(",")[0] || window.location.href) :
            new URL(window.location.href);
        const studio = currentUrl.searchParams.get("studio");
        if (studio === "1") {
            currentUrl.searchParams.delete("studio");
            history.replaceState(null, "", currentUrl.toString());
        }
        currentUrl.searchParams.set("studio", "");
        window.location.href = currentUrl.toString();
        setTimeout(() => window.location.reload(), 500);
    }
})
StudioMenuSideBar.props = {
    ...StudioMenuSideBar.props,
    isAI: { type: Boolean, optional: true },
};
