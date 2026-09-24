/** @odoo-module **/
import { FormCompiler } from "@web/views/form/form_compiler";
import { append } from "@web/core/utils/xml";
import { patch } from "@web/core/utils/patch";

patch(FormCompiler.prototype, {
    compile(node, params) {
        const res = super.compile(node, params);
        const chatterContainerHookXml = res.querySelector(".o-mail-Form-chatter");
        if (chatterContainerHookXml) {
            const formSheetCy = res.querySelector(".o_form_sheet_bg");
            const chatterContainerHookXmlSheet = chatterContainerHookXml.cloneNode(true);
            chatterContainerHookXmlSheet.classList.add('o-isInFormSheetCy', 'w-auto');
            chatterContainerHookXml.setAttribute("t-if", false);
            append(formSheetCy, chatterContainerHookXmlSheet);
        }
        return res;
    },
});