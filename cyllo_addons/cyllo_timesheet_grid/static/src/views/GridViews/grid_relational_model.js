/* @odoo-module */
import {RelationalModel} from "@web/model/relational_model/relational_model";

export class GridRelationalModel extends RelationalModel {
    static DEFAULT_LIMIT = 0;

    async load(params = {}) {
        await Promise.all([this.fetchActivityData(params), super.load(params)]);
    }

    async fetchActivityData(params) {
        this.activityData = await this.orm.searchRead("account.analytic.line", params.domain);
    }
}
