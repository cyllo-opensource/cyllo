/** @odoo-module */
import { FormLabel } from "@web/views/form/form_label";
import { patch } from '@web/core/utils/patch';
import { useService } from '@web/core/utils/hooks';
import {session} from "@web/session";

patch(FormLabel.prototype, {
/** Patch FormLabel to edit the label on double click */
    setup(){
        super.setup();
        this.orm = useService('orm');
    },
    /** Edit label via double click on it */
    async onDblClick(ev){
        if(session.is_admin){
            var InnerText = ev.srcElement.innerText
            this.first_val = InnerText
            this.access = false
            var self = this;
            self.field_name = ''
            if(ev.target.localName === 'label'){
                this.originalLabel = ev.target;
                var input = document.createElement('input');
                input.id = 'label_edit';
                input.className = 'edit_label';
                input.dataset.label_for = ev.target.getAttribute('for');
                if (InnerText.charAt(InnerText.length - 1) == '?') {
                    InnerText = InnerText.substring(0, InnerText.length - 1);
                }
                input.value = InnerText;
                self.input = input;
                self.field_name = ev.srcElement.innerText;
                this.originalLabel.parentNode.replaceChild(input, ev.target);
                document.querySelector("#label_edit").onmouseout = function() {
                    if (InnerText == document.getElementById('label_edit').value){
                        self.replaceInputWithLabel(input, InnerText, self.originalLabel);
                    }else{self.ChangeLabel(event)}
                };
            }
        }
    },
    /** Change <input> into label with old attributes **/
    replaceInputWithLabel(input, text, originalLabel) {
        var newLabel = document.createElement('label');
        /** Copy attributes from the original label to the new label **/
        Array.from(originalLabel.attributes).forEach(attr => {
            newLabel.setAttribute(attr.name, attr.value);
        });
        var originalSup = originalLabel.querySelector('sup');
        if (originalSup) {
            var newSup = document.createElement('sup');
            Array.from(originalSup.attributes).forEach(attr => {
                newSup.setAttribute(attr.name, attr.value);
            });
            newLabel.innerText = text;
            newSup.innerHTML = originalSup.innerHTML;
            newLabel.appendChild(newSup);
        }
        else{
            newLabel.innerText = text;
        }
        /** Add 'dblclick' event listeners for new label **/
        newLabel.addEventListener('dblclick', this.onDblClick.bind(this));
        input.parentNode.replaceChild(newLabel, input);
    },

     ChangeLabel(event) {
        /** Changes the label after move the mouse outside the label box */
        var self = this;
        var input = self.input
        var ModelName = this.props.record.resModel
        var ViewType = this.env.config.viewType
        var inputField = this.field_name
        var inputValue = event.srcElement.value
        var field_tech_name;
        var inputFieldName = document.querySelector("#label_edit").getAttribute('data-label_for')
        this.orm.call('ir.ui.view',
         'edit_xml_field_label', [ModelName, ViewType, inputField, inputFieldName, inputValue]
        ).then(function(result) {
            if (result === true) {
            event.srcElement.innerText = inputValue;
            event.target.parentNode.replaceChild(input, event.target);
            location.reload();
            }
        });
     }
});
