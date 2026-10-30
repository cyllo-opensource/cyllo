/** @odoo-module **/

import { Component, markup, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";

/**
 * Converts stored email signature HTML into plain text for the editor.
 */
function htmlToText(html) {
    const doc = new DOMParser().parseFromString(html || '', 'text/html');
    const result = [];
    function getText(node) {
        if (node.nodeType === Node.TEXT_NODE) {
            result.push(node.textContent);
        } else if (node.nodeType === Node.ELEMENT_NODE) {
            if (node.tagName === 'BR') {
                result.push('\n');
            }
            for (let childNode of node.childNodes) {
                getText(childNode);
            }
        }
    }

    getText(doc.body);
    return result.join('');
}

/**
 * Stores the edited signature, keeping line breaks as <br> tags.
 */
function textToHtml(text) {
    return (text || '').replace(/\n/g, '<br>');
}

/**
 * "Email Signature" editor dialog content. Opened through the dialog
 * service, which provides the environment (dialogData) the core Dialog
 * component's setup requires — rendering <Dialog> directly inside a
 * normal component tree crashes with "Cannot make the given value
 * reactive" (this.env.dialogData is then undefined).
 * Body/Chrome/footer follow the core ConfirmationDialog pattern.
 */
export class SignatureEditDialog extends Component {
    setup() {
        // Local edit buffer, seeded with the stored text: saving without
        // touching rewrites the same signature; clearing saves empty.
        this.state = useState({ draft: this.props.draft });
        this.saving = false;
    }

    onSignatureInput(ev) {
        this.state.draft = ev.target.value;
    }

    async save() {
        // Guard against double-click writing twice.
        if (this.saving) {
            return;
        }
        this.saving = true;
        try {
            await this.props.onSave(this.state.draft);
            this.props.close();
        } finally {
            this.saving = false;
        }
    }
}
SignatureEditDialog.template = "cyllo_dashboard.SignatureEditDialog";
SignatureEditDialog.components = { Dialog };
SignatureEditDialog.props = {
    close: Function,
    draft: String,
    onSave: Function,
};

// Used to scope the Notification Type radio group per panel instance.
let panelSequence = 0;

/**
 * "Account Settings" panel: editable email signature, notification type
 * and the groups / access rights shortcuts. Rendered inline on the
 * non-admin dashboard (instead of the admin-only Login History card).
 */
export class AccountSettingsPanel extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.dialogService = useService("dialog");
        // Several panels could coexist (inline card + dialog host), so the
        // Notification Type radio group is scoped to this instance.
        this.notifGroupName = `cy_notif_${++panelSequence}`;
    }

    get markupSignature() {
        return markup(this.props.nonAdmin.signature || "");
    }

    get signature() {
        return htmlToText(this.props.nonAdmin.signature || "");
    }

    get notifRadioIds() {
        return {
            email: `${this.notifGroupName}_email`,
            inbox: `${this.notifGroupName}_inbox`,
        };
    }

    /** Opens the signature editor in a service-managed dialog. */
    editSignature() {
        this.dialogService.add(SignatureEditDialog, {
            draft: this.signature,
            onSave: (draft) => this.saveSignature(draft),
        });
    }

    async saveSignature(draft) {
        const signature = textToHtml(draft);
        await this.orm.write("res.users", [this.props.userId], { signature });
        // props.nonAdmin is the dashboard's reactive state object: writing
        // it in place re-renders the panel without a full page reload.
        this.props.nonAdmin.signature = signature;
    }

    onInputNotifType(ev) {
        this.orm.write("res.users", [this.props.userId], { 'notification_type': ev.target.value });
        // Mail routing depends on the session context: refresh the interface.
        this.action.doAction("reload_context");
    }

    onClickGroups() {
        this.action.doAction({
            name: 'Groups',
            type: 'ir.actions.act_window',
            res_model: 'res.groups',
            views: [[false, 'tree'], [false, 'form']],
            target: 'current',
            context: { 'create': false, 'delete': false },
            domain: [['id', 'in', this.props.nonAdmin.groups_id]],
        });
    }

    onClickAccessRights() {
        this.action.doAction({
            name: 'Access Rights',
            type: 'ir.actions.act_window',
            res_model: 'ir.model.access',
            views: [[false, 'tree']],
            target: 'current',
            context: { 'create': false, 'delete': false },
            domain: [['id', 'in', this.props.nonAdmin.model_access]],
        });
    }

    onClickRecordRules() {
        this.action.doAction({
            name: 'Record Rules',
            type: 'ir.actions.act_window',
            res_model: 'ir.rule',
            views: [[false, 'tree']],
            target: 'current',
            context: { 'create': false, 'delete': false },
            domain: [['id', 'in', this.props.nonAdmin.rule_groups]],
        });
    }
}

AccountSettingsPanel.template = "cyllo_dashboard.AccountSettingsPanel";
AccountSettingsPanel.props = {
    nonAdmin: Object,
    notifType: { type: [String, Boolean], optional: true },
    userId: { type: Number, optional: true },
};
