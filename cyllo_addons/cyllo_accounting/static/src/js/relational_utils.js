/** @odoo-module **/
import {patch} from "@web/core/utils/patch";
import {X2ManyFieldDialog} from "@web/views/fields/relational_utils";
import {executeButtonCallback} from "@web/views/view_button/view_button_hook";
import {AlertDialog} from "@web/core/confirmation_dialog/confirmation_dialog";
import {_t} from "@web/core/l10n/translation";

patch(X2ManyFieldDialog.prototype, {
    save({saveAndNew}) {
        return executeButtonCallback(this.modalRef.el, async () => {
            if (this.record.data.create_from_payment && this.record.data.state == 'draft') {
                this.env.services.dialog.add(AlertDialog, {
                    title: _t("Error"),
                    body: _t("You cannot register payment for draft journal entries"),
                });
            } else {
                if (await this.record.checkValidity({displayNotification: true})) {
                    await this.props.save(this.record);
                    if (saveAndNew) {
                        await this.record.switchMode("readonly");
                        this.record = await this.props.addNew();
                    }
                } else {
                    return false;
                }
                if (!saveAndNew) {
                    this.props.close();
                }
                return true;
            }
        });
    }
});