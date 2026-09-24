/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import FormEditorRegistry from "@website/js/form_editor_registry";

FormEditorRegistry.add('create_ticket', {
    formFields: [{
        type: 'char',
        modelRequired: true,
        name: 'name',
        string: _t('Subject'),
    }, {
        type: 'email',
        required: true,
        fillWith: 'email',
        name: 'email',
        string: _t('Your Email'),
    }, {
        type: 'tel',
        name: 'phone',
        fillWith: 'phone',
        string: _t('Phone Number'),
    }, {
        type: 'text',
        required: true,
        name: 'description',
        string: _t('Your question'),
    }, {
        type: 'binary',
        name: 'attachment_ids',
        string: _t('Attachments'),
    }],
    fields: [{
        name: 'team_id',
        type: 'many2one',
        relation: 'helpdesk.team',
        string: _t('Helpdesk Team'),
        title: _t('Assign tickets to a helpdesk team.'),
    }],
});
