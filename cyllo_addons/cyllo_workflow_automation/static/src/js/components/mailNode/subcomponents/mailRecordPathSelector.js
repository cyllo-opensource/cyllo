/** @odoo-module */
import {RecordPathSelector} from "../../Assists/recordPathSelector/recordPathSelector";

export class MailRecordPathSelector extends RecordPathSelector {
    setup() {
        super.setup();
    }
    filterFields(defs, path) {
        if (!this.props.fieldInfo) return true;
        const { fieldInfo: { fieldDef, resModel }, operator } = this.props
        if (["ilike", "not ilike"].includes(operator)) return defs.type === "char"
        if (defs.name === "id") return true
        else if (fieldDef.type === "many2one" || fieldDef.type === "many2many" || fieldDef.type === "one2many"  ) {
            // Any relational field must stay visible so the popover can be drilled into
            // (e.g. crm.lead.team_id -> crm.team.user_id) even though its own relation
            // doesn't match the target. Otherwise intermediate hops are hidden and the
            // matching field on the related model can never be reached.
            if (defs.relation) return true
            if (["in", "not in"].includes(operator) && fieldDef.type === "many2one") return fieldDef.relation === defs.relation
            return  fieldDef.type === defs.type && fieldDef.relation.includes(defs.relation)
        } else if (fieldDef.type === "binary") {
            return false
        } else if (fieldDef.type === "selection") {
            return fieldDef.type === defs.type && resModel === this.state.model.model && fieldDef.name === defs.name
        } else {
            return fieldDef.type === defs.type
        }
        return false;
    }
}