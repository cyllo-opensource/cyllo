/** @odoo-module **/
import {
    ClientErrorDialog,
    Error504Dialog,
    RPCErrorDialog,
    ErrorDialog,
    RedirectWarningDialog,
    SessionExpiredDialog,
    WarningDialog
} from "@web/core/errors/error_dialogs";
import {patch} from "@web/core/utils/patch";

patch(WarningDialog.prototype, {
    setup() {
        super.setup(...arguments);
        this.env.bus.trigger("CY_INSTALL_ERR")
    }
})
patch(ClientErrorDialog.prototype, {
    setup() {
        super.setup(...arguments);
        this.env.bus.trigger("CY_INSTALL_ERR")
    }
})
patch(Error504Dialog.prototype, {
    setup() {
        super.setup(...arguments);
        this.env.bus.trigger("CY_INSTALL_ERR")
    }
})
patch(ErrorDialog.prototype, {
    setup() {
        super.setup(...arguments);
        this.env.bus.trigger("CY_INSTALL_ERR")
    }
})
patch(RPCErrorDialog.prototype, {
    setup() {
        super.setup(...arguments);
        this.env.bus.trigger("CY_INSTALL_ERR")
    }
})
patch(RedirectWarningDialog.prototype, {
    setup() {
        super.setup(...arguments);
        this.env.bus.trigger("CY_INSTALL_ERR")
    }
})
patch(SessionExpiredDialog.prototype, {
    setup() {
        super.setup(...arguments);
        this.env.bus.trigger("CY_INSTALL_ERR")
    }
})