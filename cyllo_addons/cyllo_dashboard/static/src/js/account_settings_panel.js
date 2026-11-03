/** @odoo-module **/

import { Component, markup, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";

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

function textToHtml(text) {
    return (text || '').replace(/\n/g, '<br>');
}

export class SignatureEditDialog extends Component {
    setup() {

        this.state = useState({ draft: this.props.draft });
        this.saving = false;
    }

    onSignatureInput(ev) {
        this.state.draft = ev.target.value;
    }

    async save() {

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

let panelSequence = 0;

export class AccountSettingsPanel extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.dialogService = useService("dialog");

        this.notifGroupName = `cy_dashboard_notif_${++panelSequence}`;
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

    editSignature() {
        this.dialogService.add(SignatureEditDialog, {
            draft: this.signature,
            onSave: (draft) => this.saveSignature(draft),
        });
    }

    async saveSignature(draft) {
        const signature = textToHtml(draft);
        await this.orm.write("res.users", [this.props.userId], { signature });

        this.props.nonAdmin.signature = signature;
    }

    onInputNotifType(ev) {
        this.orm.write("res.users", [this.props.userId], { 'notification_type': ev.target.value });

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
