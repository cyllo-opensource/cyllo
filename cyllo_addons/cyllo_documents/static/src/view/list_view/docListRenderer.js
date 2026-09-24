/** @odoo-module */
import {ListRenderer} from '@web/views/list/list_renderer';
export class DocListRenderer extends ListRenderer {

    onCellClicked(record, column, ev) {
        if (column.name === 'name') {
            this.props.openRecord(record);
        } else {
            return super.onCellClicked(record, column, ev);
        }
    }
}
