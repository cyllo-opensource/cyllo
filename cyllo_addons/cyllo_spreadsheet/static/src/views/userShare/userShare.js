/** @odoo-module */
import {Component, useState, onWillStart} from "@odoo/owl";
import {Dialog} from "@web/core/dialog/dialog";
import {MultiRecordSelector} from "@web/core/record_selectors/multi_record_selector";
import {useService} from "@web/core/utils/hooks";
import {Dropdown} from "@web/core/dropdown/dropdown";
import {DropdownItem} from "@web/core/dropdown/dropdown_item";


export class UserShare extends Component {
    static components = {Dialog, MultiRecordSelector, Dropdown, DropdownItem}
    static template = "userShare"

    setup() {
        this.orm = useService('orm')
        onWillStart(this.loadAccessData)
        this.state = useState({
            users: [],
            accessRecord: [],
            accessLevel: 'viewer'
        })
    }

    async loadAccessData() {
        this.state.accessRecord = await this.orm.call("spreadsheet.sheet", "get_access_data", [this.props.selected])
    }

    get userDomain() {
        return [['id', 'not in', this.state.users], ['share', '=', false]]
    }

    handleUserSelect(users) {
        this.state.users = users
    }

    get multiRecordProps() {
        return {
            placeholder: "Users",
            resModel: "res.users",
            resIds: this.state.users,
            domain: this.userDomain,
            update: this.handleUserSelect.bind(this),
        }
    }

    toggleAccess(access) {
        this.state.accessLevel = access
    }

    get accessData() {
        const {accessLevel, users} = this.state
        return {
            access_level: accessLevel,
            users,
        }
    }

    async handleSubmit() {
        if (this.state.users.length) {
            await this.orm.call("spreadsheet.sheet", "apply_access_to_users", [this.props.selected], this.accessData)
        }
        this.props.close()
    }

    async toggleAccessBacked(resid, user, access, isAdd) {
        await this.orm.call("spreadsheet.sheet", "toggle_access_level", [resid, user, access, isAdd])
        const record = this.state.accessRecord.find(item => item.id === resid).access.find(item => item.id === user)
        if (record) {
            if (access === 'read' && !isAdd) {
                record.read = false;
                record.write = false;
            }
            if (access === 'write' && isAdd) {
                record.read = true;
                record.write = true;
            }
            if (access === 'read' && isAdd) {
                record.read = true;
            }
            if (access === 'write' && !isAdd) {
                record.write = false;
            }
        }
    }

    handleClose() {
        this.props.close();
    }
}