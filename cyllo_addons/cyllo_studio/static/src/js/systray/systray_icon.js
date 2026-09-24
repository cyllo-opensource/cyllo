/** @odoo-module **/
import {
    Systray
} from "@cyllo_web/js/systray/cyllo_systray/systray";
import {
    patch
} from "@web/core/utils/patch";
import {
    _t
} from "@web/core/l10n/translation";

const { useState, onWillStart } = owl;

patch(Systray.prototype, {
    setup() {
        super.setup();
        this._studioAccess = useState({ hasAccess: false });
        onWillStart(async () => {
            const isUser = await this.env.services.user.hasGroup(
                "cyllo_studio.group_cyllo_studio_user"
            );
            const isAdmin = await this.env.services.user.hasGroup(
                "cyllo_studio.group_cyllo_studio_admin"
            );
            this._studioAccess.hasAccess = !!(isUser || isAdmin);
        });
    },
    async _onClick() {
        sessionStorage.setItem('UndoRedo', JSON.stringify([]));
        sessionStorage.setItem('ReDO', JSON.stringify([]));
        const model = new URLSearchParams(location.hash.slice(1)).get('model');
        const viewType = new URLSearchParams(location.hash.slice(1)).get('view_type');
        if (model === 'res.config.settings') {
            return this.env.services.notification.add(
                _t("Studio mode cannot be activated from Settings!"), {
                type: 'danger',
                title: _t('Restricted')
            })
        }
        if (["workflowCard", "reconcile"].includes(viewType)){
            return this.env.services.notification.add(
                _t("Studio mode cannot be activated in " + viewType + " view!"), {
                type: 'danger',
                title: _t('Restricted')
            });
        }
        if (model === 'pos.order' && viewType === 'form') {
            return this.env.services.notification.add(
                _t("Studio mode cannot be activated from this view!"), {
                type: 'danger',
                title: _t('Restricted')
            });
        }
        // Block Studio in specific models
        const restrictedModels = ['ir.module.module', 'res.users', 'res.company', 'login.user.detail', 'shortcut.menu',
            'plan.allocation', 'document.file', 'request.document', 'document.template.request', 'crm.lead', 'dashboard.sheet',
            'dashboard.config', 'allocation.type','work.auto','document.request.template'];
        if (restrictedModels.includes(model)) {
            return this.env.services.notification.add(
                _t("Studio mode cannot be activated from this view!"), {
                type: 'danger',
                title: _t('Restricted')
            });
        }
        const appId = parseInt(localStorage.getItem('cy_selected_app')) || false
        const currentUrl = new URL(window.location.href);
        const urlParams = currentUrl.searchParams;
        urlParams.delete("studio");
        urlParams.set("studio", "1");
        window.location.href = currentUrl.toString();
    },
});