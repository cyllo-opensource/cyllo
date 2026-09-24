/** @odoo-module */
import { Dialog } from "@web/core/dialog/dialog";
import { Component, onWillStart } from "@odoo/owl";
import { Record } from "@web/model/record";
import { Many2OneField } from "@web/views/fields/many2one/many2one_field";
import { CharField } from "@web/views/fields/char/char_field";
import { Many2ManyTagsField } from "@web/views/fields/many2many_tags/many2many_tags_field";
import { IntegerField } from "@web/views/fields/integer/integer_field";
import { useService } from "@web/core/utils/hooks";

class DeleteOnlyMany2ManyTagsField extends Many2ManyTagsField {
    getTagProps(record) {
        var props = super.getTagProps(...arguments);
        props.onDelete = () => this.deleteTag(record.id)
        return props
    }
}

export class ConfigurationDialog extends Component {
    // This is a class for configuration dialog box
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.data = {}
        onWillStart(async() => {
            this.hasLinkedMenu = [];
            if (this.props.id) {
                const data = await this.orm.read("dashboard.config", [this.props.id], ['ir_menu_ids'])
                this.hasLinkedMenu = data[0]?.ir_menu_ids || []
            }
        })
    }

    /**
     * Get properties for the Record component.
     * @returns {object} - Record properties.
     */
    get recordProps() {
        var related = {
            display_name: {
                name: "display_name",
                type: "char"
            }
        }
         var theme_id = {
             type: "many2one",
             relation: "dashboard.theme",
             string: "Theme",
             related: {
                activeFields: related,
                fields: related,
             },
         }
         var banner_id = {
             type: "many2one",
             relation: "dashboard.banner",
             string: "Banner",
             related: {
                activeFields: related,
                fields: related,
             },
         }
         var name = {
             type: "char",
             string: "Name",
         }
         var group_ids = {
             type: "many2many",
             string: "Groups",
             relation: "res.groups",
             related: {
                activeFields: related,
                fields: related,
             },
         }
         var user_ids = {
             type: "many2many",
             string: "users",
             relation: "res.users",
             related: {
                activeFields: related,
                fields: related,
             },
         }
         var ir_menu_ids = {
             type: "many2many",
             string: "Linked Menus",
             relation: "ir.ui.menu",
             related: {
                activeFields: related,
                fields: related,
             },
         }
         var company_id = {
            type: "many2one",
            relation: "res.company",
            string: "Company",
            related: {
                activeFields: related,
                fields: related,
            },
        }
         var fields = { theme_id, name, group_ids, user_ids, ir_menu_ids, banner_id, company_id }
         var self = this
         return {
             mode: "edit",
             onRecordChanged: (record, changes) => {
                for (var key in changes){
                    self.data[key] = changes[key]
                }
             },
             resModel: "dashboard.config",
             resId: this.props.id,
             fieldNames: fields,
             activeFields: fields,
         };
    }
    /**
     * Handle configuration save action.
     */
    async onConfigSave() {
        if(this.props.id){
            await this.orm.write("dashboard.config", [this.props.id], this.data);
            if(this.data.theme_id){
                this.props.applyTheme(this.data.theme_id)
            }
            this.props.onClickSave(this.data)
            if (this.data.ir_menu_ids) {
                this.action.doAction("reload_context");
            }
        } else {
            await this.orm.create("dashboard.config", [this.data])
            this.action.doAction('soft_reload')
        }
        this.props.close()
    }
    get defaultConfProps() {
        return {
            canCreate: false,
            canCreateEdit: false,
            canQuickCreate: false,
        }
    }

}
// Define the template and components for the ConfigurationDialog component
ConfigurationDialog.template = "cyllo_analytics.ConfigurationDialog";
ConfigurationDialog.defaultProps = {
    onClickSave: () => {}
};
ConfigurationDialog.components = { Dialog, Record, Many2OneField, CharField , Many2ManyTagsField, IntegerField, DeleteOnlyMany2ManyTagsField};