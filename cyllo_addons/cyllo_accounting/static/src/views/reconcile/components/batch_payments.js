/** @odoo-module **/
import { registry } from "@web/core/registry";
import { View } from "@web/views/view";
import { Component, onWillStart,useState, markup, onError } from  "@odoo/owl";
import { escape } from "@web/core/utils/strings";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";



export class BatchPayments extends Component {
    static template = "batchPayments";
    static components = {
        View
    };
    setup() {
        this.viewService = useService("view");
        this.resModel = this.props.resModel || "batch.payment";
        this.state = useState({
            result: {},
            selectedRecord: null,
        })
        onWillStart(this.loadView)
    }
    async loadView() {

        const result = await this.viewService.loadViews({
                resModel: this.resModel,
                views: [
                    [false, "list"]
                ],
                options: { actionId: this.props.actionId || undefined }
            }

        )
        this.state.result = result;


    }
     async onBatchRecordSelect(resId) {
        try {
            // First get the batch payment record
            const batchPayment = await this.env.services.orm.read(
                this.resModel,
                [resId],
                ["date", "name", "payment_ids"]
            );

            if (batchPayment && batchPayment[0].payment_ids.length > 0) {
                // Get payment details
                const payments = await this.env.services.orm.read(
                    "account.payment",
                    batchPayment[0].payment_ids,
                    ["name", "date", "amount", "partner_id","move_id","move_type"]
                );

                // Get move lines for each payment
                const moveIds = payments.map(payment => payment.move_id[0]);
                const accountMoveLines = await this.env.services.orm.searchRead(
                    "account.move.line",
                    [["move_id", "in", moveIds]],
                    ["name", "date", "partner_id", "debit", "credit", "account_id", "amount_residual","move_id","move_type"]
                );

                // Remove unwanted move line
                const FilterMoveLines = accountMoveLines.filter(
                line => !line.account_id[1].includes("121000 Account Receivable") &&
                        !line.account_id[1].includes("211000 Account Payable")
                );

                // Adjust move lines for 101403 Outstanding Receipts
                const adjustedMoveLines = FilterMoveLines.map(line => {
                if (line.account_id[1].includes("101403 Outstanding Receipts") && line.debit > 0) {
                    // Swap debit to credit
                    return {
                        ...line,
                        credit: line.debit,
                        debit: 0
                    };
                }
                if (line.account_id[1].includes("101404 Outstanding Payments") && line.credit > 0) {
                    // Swap debit to credit
                    return {
                        ...line,
                        debit: line.credit,
                        credit: 0
                    };
                }

                return line; // Leave other lines unchanged
                });

                this.props.onBatchRecordSelect(adjustedMoveLines);
            }
        } catch (error) {
            console.error("Error in batch payment selection:", error);
        }
    }

    get viewProps() {
        const translatedText = _t("No records found!");
        return {
            display: {
                searchPanel: false
            },
            editable: false,
            noBreadcrumbs: true,
            noContentHelp: markup(`<p>${escape(translatedText)}</p>`),
            showButtons: false,
            selectRecord: (resId) => {
                this.onBatchRecordSelect(resId);
            },
            onSelectionChanged: (resIds) => {
            },
            context: this.props.context,
            domain: [
                ["state", "!=", 'reconciled']
            ],
            dynamicFilters: [{
                description: _t("Bank"),
                domain: [
                    ["journal_id.type", "=", 'bank']
                ]
            }],
            resModel: this.resModel,
            searchViewId: undefined,
            type: 'list'
        }
    }
}

