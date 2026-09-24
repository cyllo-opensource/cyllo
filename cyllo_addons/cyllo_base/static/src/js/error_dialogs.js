/** @odoo-module **/
import { odooExceptionTitleMap, WarningDialog, ErrorDialog, ClientErrorDialog,
NetworkErrorDialog, RPCErrorDialog, SessionExpiredDialog } from "@web/core/errors/error_dialogs";
import { patch } from "@web/core/utils/patch";
import { _lt } from "@web/core/l10n/translation";
import { _t } from "@web/core/l10n/translation";

/**
 * Set custom titles for error and warning dialogs to indicate system-level issues.
*/
ErrorDialog.title = _lt("System Error");
ClientErrorDialog.title = _lt('System Client Error');
SessionExpiredDialog.title = _lt('System Session Expired');
NetworkErrorDialog.title = _lt('System Network Expired');
patch(RPCErrorDialog.prototype, {
    /**
     * Infers and updates the title of the RPC error dialog based on the error type.
     */
    inferTitle() {
        if (this.props.exceptionName && odooExceptionTitleMap.has(this.props.exceptionName)) {
            this.title = odooExceptionTitleMap.get(this.props.exceptionName).toString();
            return;
        }
        if (!this.props.type) {
            return;
        }
        switch (this.props.type) {
            case "server":
                this.title = _t("System Server Error");
                break;
            case "script":
                this.title = _t("System Client Error");
                break;
            case "network":
                this.title = _t("System Network Error");
                break;
        }
    }
});

patch(WarningDialog.prototype, {
    /**
     * Overrides the setup method of the WarningDialog prototype to set a common title for all warnings.
     */
    setup() {
        super.setup();
        this.title = this.inferTitle();
    },

    inferTitle() {
        if (this.props.exceptionName && odooExceptionTitleMap.has(this.props.exceptionName)) {
            return odooExceptionTitleMap.get(this.props.exceptionName).toString();
        }
        return this.props.title || _t("Cyllo Warning");
    }
});