/** @odoo-module **/
import { registry } from "@web/core/registry";
import { View } from "@web/views/view";
import { Component, onWillStart, useState, markup, onError, useEffect } from "@odoo/owl";
import { escape } from "@web/core/utils/strings";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class ViewWrapper extends Component {
    static template = "viewWrapper";
    static components = {
        View
    };

    setup() {
        this.viewService = useService("view");
        this.orm = useService("orm");
        this.resModel = this.props.resModel || "account.move.line";
        this.state = useState({
            arch: null,
            fields: {},
            partnerId: null,
            showView: true,
            matchingRecords: [],
            listViewId: false,
        });
        useEffect(() => {
            this.state.showView = false;
            setTimeout(() => this.state.showView = true, 50)
        }, () => [this.props.selectedRecord?.data?.partner_id])

        onWillStart(async () => {
            this.state.listViewId = await this.loadView();
        });
    }

    async loadView() {
         return await this.orm.call(this.resModel,"get_js_list_view",[],);
    }

    async onRecordSelect(resId) {
        const selectedRecord = await this.env.services.orm.read("account.move.line", [resId], [
            "date",
            "account_id",
            "partner_id",
            "name",
            "debit",
            "credit",
            "amount_residual",
            "move_id",
            "move_type",
            "amount_currency",
            "amount_residual_currency",
            "currency_id",
            "is_same_currency",
            "currency_rate",
            "company_currency_id",
        ]);
        this.props.onRecordSelect(selectedRecord)
    }


    get viewProps() {
        const translatedText = _t("No records found!");
        const domain = [
            "&",
            ["amount_residual", "!=", 0],
            ["account_id.reconcile", "=", true],
            ["company_id", "=", this.props.companyId]
        ];

        return {
            type: "list",
            display: {
                searchPanel: false,
            },
            editable: false,
            noBreadcrumbs: true,
            noContentHelp: markup(`<p>${escape(translatedText)}</p>`),
            showButtons: false,
            selectRecord: (resId) => this.onRecordSelect(resId),
            onSelectionChanged: (resIds) => {
            },
            context: this.props.context,
            domain: domain,
            dynamicFilters: this.dynamicFilters,
            resModel: this.resModel,
            searchViewId: false,
            viewId: this.state.listViewId
        };
    }

    get dynamicFilters() {
        const partner = this.props.selectedRecord?.data?.partner_id;
        if (partner) {
            return [{
                description: _t("Posted") + " \u2022 " + _t("Partner: %s", partner[1]),
                domain: [
                    ["parent_state", "=", "posted"],
                    ["partner_id", "=", partner[0]]
                ]
            }];
        }
        return [{
            description: _t("Posted"),
            domain: [
                ["parent_state", "=", "posted"]
            ]
        }];
    }
}
