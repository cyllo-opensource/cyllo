/* @odoo-module */
import { Component, useEffect, useState, onMounted, onWillStart, onWillUpdateProps, onWillDestroy, useExternalListener } from "@odoo/owl";
import { ReconcileLines } from "./components/reconcile_lines";
import { useService } from "@web/core/utils/hooks";
import { Notebook } from "@web/core/notebook/notebook";
import { ViewWrapper } from "@cyllo_accounting/views/reconcile/components/view_wrapper/view_wrapper";
import { ManualOperation } from "./components/manual_operation";
import { BatchPayments } from "./components/batch_payments";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";
import { session } from "@web/session";
import { formatCurrency } from "@web/core/currency";
import { DateTimeInput } from "@web/core/datetime/datetime_input";
import { Chatter } from "@mail/core/web/chatter";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";


export const PAGES = [];

export class ReconcileRenderer extends Component {
    setup() {
        this.actionService = useService("action");
        this.company = useService("company");
        this.notificationService = useService("notification");
        this.orm = useService('orm');
        this.action = useService("action");
        this.formatCurrency = formatCurrency;
        this.state = useState({
            records: this.props.list.records || [],
            selectedRecord: null,
            reconcileLines: [],
            counterpartLines: [],
            balanceAmount: 0,
            defaultPage: "match_e_entries",
            showDefaultButtons: true,
            writeOffButtons: [],
            isWriteOffActive: false,
            partnerAccounts: {
                receivable: false,
                payable: false,
                suspense: false,
            },
            showAnalytic: false,
            date: this.getCurrentDate(),
            paymentRef: "",
            amount: null,
            partner: null,
            defaultJournalAccount: null,
            selectedJournalAccount: null,
            selectedLine: null,
            selectedLineIndex: -1,
            isReconciled: false,
            strikeThroughRemoved: false,
            allowReconcile: false,
            isLoading: false,
            hasTaxes: false,
            isSameCurrency: true,
            companyAccounts: null,
            foreignCurrency: null,
            foreignAmount: null,
            currency: null,
        });

        // Bind methods to the component instance
        this.onRecordSelect = this.onRecordSelect.bind(this);
        this.onBatchRecordSelect = this.onBatchRecordSelect.bind(this);
        this.onCloseCreate = this.onCloseCreate.bind(this);
        this.hasAnalyticDistribution = this.hasAnalyticDistribution.bind(this);

        onWillStart(async () => {
            await this.getCompanyData();
            await this.getJournalAccounts();
            await this.getCurrencies();

            if (this.props.list.records.length > 0) {
                this.state.selectedRecord = this.props.list.records[0];
                try {
                    const sessionData = JSON.parse(sessionStorage.getItem("selected_record"));
                    if (sessionData) {
                        const recordId = sessionData.id
                        const recordIndex = this.props.list.records.findIndex((rec) => rec.data.id === recordId)
                        if (recordIndex > -1) {
                            this.state.selectedRecord = this.props.list.records[recordIndex]
                        }
                    }
                }
                catch (e) { }
                if (this.state.selectedRecord) {
                    await this.fetchPartnerAccounts(this.state.selectedRecord);
                    await this.addSuggestedEntries();
                }
            }
            if (this.state.selectedRecord) {
                try {
                    const reconcileData = this.state.selectedRecord.data.reconcile_session_data?.data
                    if (reconcileData) {
                        this.state.reconcileLines = reconcileData.reconcileLines
                    }
                } catch (e) {
                    console.error(e)
                }
            }
        });

        onWillUpdateProps((nextProps) => {
            this.state.records = nextProps.list.records;
            this.state.selectedRecord = nextProps.list.records[0];
            this.computeSuspenseAccount()
        });

        this.onLineClick = this.onLineClick.bind(this);

        onMounted(async () => {
            await this.checkWriteOffRule();
            await this.getDefaultCurrency();

            if (this.state.reconcileLines.length > 0) {
                this.onLineClick(this.state.reconcileLines[0]);
            }
        });

        onWillDestroy(() => {
            // Store the selected record id to session
            try {
                if (this.state.selectedRecord?.data?.id) {
                    sessionStorage.setItem("selected_record", JSON.stringify({id: this.state.selectedRecord.data.id}));
                }
            }
            catch (e) { }
        });

        useExternalListener(window, "beforeunload", () => {
            // Store the selected record id to session
            try {
                if (this.state.selectedRecord?.data?.id) {
                    sessionStorage.setItem("selected_record", JSON.stringify({id: this.state.selectedRecord.data.id}));
                }
            }
            catch(e){}
        })

        useEffect(() => {
            if (this.state.selectedRecord) {
                // Check if any line or the journal is not in company currency so that the foreign currency column is shown
                this.state.isSameCurrency = this.state.selectedRecord.data.foreign_currency_id
                    ? false
                    : this.state.reconcileLines.find(line => line.is_same_currency === false)
                    ? false
                    : true;

                if (this.state.selectedJournalAccount.id !== this.state.selectedRecord.data?.account_id[0]) {
                    const selectedJournalAccount = this.chartOfAccounts.find(
                            (account) => account.id === this.state.selectedRecord.data?.account_id[0]
                    )
                    if (!selectedJournalAccount.currency_id) {
                        selectedJournalAccount.currency_id = this.companies.find(
                            (company) => company.id === selectedJournalAccount.company_id?.[0]
                        )?.currency_id
                    }
                    selectedJournalAccount.display_name = `${selectedJournalAccount.code} ${selectedJournalAccount.name}`;
                    this.state.selectedJournalAccount = selectedJournalAccount
                    this.getCurrencies();
                    this.getDefaultCurrency();
                }

                this.fetchPartnerAccounts(this.state.selectedRecord);
                this.computeSuspenseAccount();
                this.checkAllowReconcile();
                this.computeHasTaxes();
            }
        }, () => [this.state.reconcileLines, this.state.selectedRecord]);
    }

    hasAnalyticDistribution() {
        if (!this.state.reconcileLines || this.state.reconcileLines.length === 0) {
            return false;
        }
        return this.state.reconcileLines.some(line => line.analytic_distribution);
    }

    async onUpdatePartner(ev) {
        if (ev && ev.length > 0) {
            const partnerId = ev[0].id;
            const getRecord = await this.orm.read('res.partner', [partnerId], ['id', 'display_name']);
            if (getRecord && getRecord.length > 0) {
                this.state.partner = getRecord[0];
            }
        }
    }

    async onUpdateForeignCurrency(ev) {
        if (ev && ev.length > 0) {
            const currencyId = ev[0].id;
            const foreignCurrency = this.currencies.find(currency => currency.id === currencyId);
            if (foreignCurrency) {
                this.state.foreignCurrency = foreignCurrency;
                const baseAmount = this.state.amount * this.state.currency.inverse_rate
                this.state.foreignAmount = baseAmount * foreignCurrency.rate
            }
        } else {
            this.state.foreignCurrency = null;
            this.state.foreignAmount = null;
        }
    }

    onChangeAmount(ev) {
        let value = ev.target.value;
        let filteredValue = value.replace(/[^0-9.-]/g, '');
        if (filteredValue.includes('-')) {
            filteredValue = '-' + filteredValue.replace(/-/g, '');
        }
        const decimalParts = filteredValue.split('.');
        if (decimalParts.length > 2) {
            filteredValue = decimalParts[0] + '.' + decimalParts.slice(1).join('');
        }
        this.state.amount = filteredValue;
        ev.target.value = filteredValue;
        const baseAmount = filteredValue * this.state.currency?.inverse_rate
        this.state.foreignAmount = baseAmount * this.state.foreignCurrency?.rate
    }

    onChangeForeignAmount(ev) {
        let value = ev.target.value;
        let filteredValue = value.replace(/[^0-9.-]/g, '');
        if (filteredValue.includes('-')) {
            filteredValue = '-' + filteredValue.replace(/-/g, '');
        }
        const decimalParts = filteredValue.split('.');
        if (decimalParts.length > 2) {
            filteredValue = decimalParts[0] + '.' + decimalParts.slice(1).join('');
        }
        this.state.foreignAmount = filteredValue;
        ev.target.value = filteredValue;
        const baseAmount = filteredValue * this.state.foreignCurrency?.inverse_rate
        this.state.amount = baseAmount * this.state.currency?.rate
    }

    checkAllowReconcile() {
        // Return allow reconciliation based on suspense line presence in reconcile lines
        let suspenseLine = this.state.reconcileLines.filter(line => line.is_suspense && !line.tax_id)
        try {
            const suspenseAccount = this.state.partnerAccounts.suspense
            let suspenseAccountId = false
            if (suspenseAccount.length) {
                suspenseAccountId = suspenseAccount[0]
                suspenseLine = this.state.reconcileLines.filter(line => !line.tax_id && line.account_id[0] === suspenseAccountId)
            }
        } catch (e) {
            console.error("Cannot check allow reconcile:", e)
        }
        if (suspenseLine.length) {
            this.state.allowReconcile = false
        } else {
            this.state.allowReconcile = true
        }

    }

    computeHasTaxes() {
        const hasTaxes = this.state.reconcileLines.some(line => {
            const hasTax = (line.tax_id || (line.tax_ids && line.tax_ids.length > 0));
            return hasTax;
        });
        this.state.hasTaxes = hasTaxes;
    }

    computeExchangeDifference(line) {
        const data = this.state.selectedRecord?.data;
        if (!line.is_same_currency && !line.is_computed && data && (data.foreign_currency_id || data.currency_id[0] != this.companyData.currency_id[0])) {
            const lineAmountInBase = Math.round(line.amount_residual * 100) / 100;
            //bank amount in company currency equal to current currency_rate or rate in bank line if same currency as line
            const currencyRateToCheck = (data.currency_id.id === line.currency_id?.[0])
                ? data.currency_rate
                : this.currencies.find(currency => currency.id === line.currency_id?.[0])?.rate;
            const amountToCheck = Math.round((line.amount_residual_currency / currencyRateToCheck) * 100) / 100;
            const difference = amountToCheck - lineAmountInBase;
            return Math.round(difference * 100) / 100;
        } else return 0;
    }

    computeSuspenseAccount() {
        // Compute the suspense line or partner line based on reconcile data
        if (!this.state.selectedRecord?.data) return;

        const userLines = this.state.reconcileLines.filter(line => !line.is_computed);
        const existingComputedLine = this.state.reconcileLines.find(line => line.is_computed && !line.is_manual_suspense && !line.tax_id);
        const existingSuspenseLine = this.state.reconcileLines.find(line => line.is_suspense && !line.tax_id);
        const existingPartnerLine = this.state.reconcileLines.find(line => line.is_computed && line.partner_account && !line.tax_id);

        // Get indices of existing lines
        const existingSuspenseLineIndex = this.state.reconcileLines.findIndex(line => line.is_suspense && !line.tax_id);
        const existingPartnerLineIndex = this.state.reconcileLines.findIndex(line => line.is_computed && line.partner_account && !line.tax_id);

        const totalUserAmount = userLines.reduce((sum, line) => {
            return sum + (line.amountInLine || line.amount_residual || 0);
        }, 0);
        const data = this.state.selectedRecord.data;
        const bankAmount = data.amount / data.currency_rate;
        let totalAmountResidual = bankAmount - totalUserAmount;
        // fetch foreign currency and its corresponding value
        let foreignCurrencyId = data.foreign_currency_id || data.currency_id;
        let amountInCurrency = data.foreign_currency_rate !== 0
            ? data.foreign_currency_rate * (totalAmountResidual)
            : data.currency_rate * (totalAmountResidual);

        totalAmountResidual = Math.round((totalAmountResidual) * 100) / 100;
        const suspenseAccount = this.state.partnerAccounts.suspense;

        let newComputedLine = null;
        // Generate or reuse suspense_line_id for both partner and suspense lines
        let suspenseLineId = existingComputedLine?.suspense_line_id ||
            existingSuspenseLine?.suspense_line_id ||
            existingPartnerLine?.suspense_line_id ||
            this.generateSuspenseLineId();


        if (totalAmountResidual !== 0) {
            const partner = this.state.selectedRecord.data.partner_id;

            if (partner) {
                const partnerAccounts = this.state.partnerAccounts;
                const amount = Math.round(totalAmountResidual * 100) / 100;

                const account = (
                    this.state.selectedRecord.data.amount > 0
                        ? partnerAccounts.receivable
                        : partnerAccounts.payable
                );

                if (!account) {
                    console.error("Partner account not found");
                    return;
                }

                newComputedLine = {
                    id: true,
                    account_id: account,
                    partner_id: partner,
                    amount_residual: totalAmountResidual,
                    is_computed: true,
                    is_manual_suspense: false,
                    partner_account: (
                        this.state.selectedRecord.data.amount > 0
                            ? 'receivable'
                            : 'payable'
                    ),
                    amount_formatted: this.formatCurrency(totalAmountResidual, this.companyData.currency_id[0]),
                    suspense_line_id: suspenseLineId,
                    tax_ids: existingComputedLine?.tax_ids || existingPartnerLine?.tax_ids || false,
                    currency_id: foreignCurrencyId,
                    is_same_currency: data.foreign_currency_id ? false : true,
                    amount_currency: amountInCurrency,
                    company_currency_id: this.companyData.currency_id,
                };
            } else {
                if (!suspenseAccount) {
                    console.error("Suspense account not found");
                    return;
                }

                newComputedLine = {
                    account_id: suspenseAccount,
                    amount_residual: totalAmountResidual,
                    payment_ref: existingSuspenseLine?.payment_ref || this.selectedData?.payment_ref,
                    is_computed: true,
                    is_suspense: true,
                    is_manual_suspense: false,
                    suspense_line_id: suspenseLineId,
                    currency_id: foreignCurrencyId,
                    is_same_currency: data.foreign_currency_id ? false : true,
                    amount_currency: amountInCurrency,
                    company_currency_id: this.companyData.currency_id,
                };
            }

            // Update existing lines at their current indices or add new one
            let newReconcileLines = [...this.state.reconcileLines];

            // Handle partner line update
            if (existingPartnerLine && newComputedLine?.partner_account) {
                newReconcileLines[existingPartnerLineIndex] = {
                    ...existingPartnerLine,
                    ...newComputedLine,
                    amount_residual: totalAmountResidual,
                    amount_formatted: this.formatCurrency(totalAmountResidual, this.companyData.currency_id[0])
                };
            }
            // Handle suspense line update
            else if (existingSuspenseLine && newComputedLine?.is_suspense) {
                newReconcileLines[existingSuspenseLineIndex] = {
                    ...existingSuspenseLine,
                    ...newComputedLine,
                    amount_residual: totalAmountResidual,
                    amount_formatted: this.formatCurrency(totalAmountResidual, this.companyData.currency_id[0])
                };
            }
            // Add new line if no existing line of the appropriate type
            else if (newComputedLine) {
                // Try to maintain position near the end but before any tax lines
                const insertIndex = Math.max(
                    existingSuspenseLineIndex,
                    existingPartnerLineIndex,
                    userLines.length
                );
                newReconcileLines.splice(insertIndex, 0, newComputedLine);
            }
            // Remove existing line if no new computed line is needed
            else if ((existingSuspenseLine && !newComputedLine) || (existingPartnerLine && !newComputedLine)) {
                const indexToRemove = existingSuspenseLineIndex !== -1 ? existingSuspenseLineIndex : existingPartnerLineIndex;
                newReconcileLines = [
                    ...newReconcileLines.slice(0, indexToRemove),
                    ...newReconcileLines.slice(indexToRemove + 1)
                ];
            }

            // Only update state if lines have changed
            if (
                (newComputedLine && existingComputedLine && !this.areLinesEqual(newComputedLine, existingComputedLine)) ||
                (!newComputedLine && existingComputedLine) ||
                (newComputedLine && !existingComputedLine)
            ) {
                this.state.reconcileLines = newReconcileLines;
            }
        } else if (existingSuspenseLineIndex !== -1 || existingPartnerLineIndex !== -1) {
            let updatedLines = [...this.state.reconcileLines];
            [existingSuspenseLineIndex, existingPartnerLineIndex].filter(
                i => i !== -1).forEach(i => {
                updatedLines = [
                    ...updatedLines.slice(0, i),
                    ...updatedLines.slice(i + 1)
                ];
            });
            this.state.reconcileLines = updatedLines
        }
    }

    areLinesEqual(line1, line2) {
        // Return whether the two lines are equal or not
        return (
            line1.account_id === line2.account_id &&
            line1.amount_residual === line2.amount_residual
        );
    }

    generateSuspenseLineId() {
        return `sl_id_${Date.now()}_${Math.floor(Math.random() * 1000)}`;
    }

    onRecordSelect(record) {
        this.state.reconcileLines = this.state.reconcileLines.filter((line) => !line.suspense_line_id && !line.tax_id && !line.is_computed)
        const selectedData = this.state.selectedRecord?.data;
        if (!selectedData) return;

        const SAmount = (selectedData.amount / selectedData.currency_rate);
        const strikeTroughLine = this.state.reconcileLines.find(line => line.amountInLine === SAmount)
        if (strikeTroughLine) {
            strikeTroughLine.amountInLine = false
            strikeTroughLine.amount_currency = strikeTroughLine.amount_residual_currency
            this.state.strikeThroughRemoved = true
        }
        const existingLineIndex = this.state.reconcileLines.findIndex(line => line.id === record[0].id);
        // foreign exchange difference line
        const existingExchangeDiffLineIndex = this.state.reconcileLines.findIndex(line => line.is_exchange_diff);
        const lineExchangeDifference = this.computeExchangeDifference(record[0]);

        if (existingLineIndex !== -1) {
            if (existingExchangeDiffLineIndex !== -1 && lineExchangeDifference) {
                const updatedLines = [...this.state.reconcileLines];
                const updatedLine = {...updatedLines[existingExchangeDiffLineIndex]};
                updatedLine.amountInLine -= lineExchangeDifference;
                updatedLine.amount_residual -= lineExchangeDifference;
                updatedLines[existingExchangeDiffLineIndex] = updatedLine;
                if (updatedLine.amount_residual === 0) {
                    updatedLines.splice(existingExchangeDiffLineIndex, 1);
                }
                this.state.reconcileLines = updatedLines;
            }

            this.state.reconcileLines = [
                ...this.state.reconcileLines.slice(0, existingLineIndex),
                ...this.state.reconcileLines.slice(existingLineIndex + 1)
            ];
        } else {
            const line = {
                ...record[0],
                amountInLine: null,
            };
            const lineAmount = line.amount_residual;
            let exchangeDifferenceLine = null;
            if (lineExchangeDifference !== 0) {
                if (existingExchangeDiffLineIndex !== -1) {
                    const updatedLines = [...this.state.reconcileLines];
                    exchangeDifferenceLine = {...updatedLines[existingExchangeDiffLineIndex]};
                    updatedLines.splice(existingExchangeDiffLineIndex, 1);
                    this.state.reconcileLines = updatedLines;
                    exchangeDifferenceLine.amountInLine += lineExchangeDifference;
                    exchangeDifferenceLine.amount_residual += lineExchangeDifference;
                } else {
                    exchangeDifferenceLine = {
                        account_id: (
                            lineExchangeDifference < 0
                                ? this.companyData.expense_currency_exchange_account_id
                                : this.companyData.income_currency_exchange_account_id
                        ),
                        amount_residual: Math.round(lineExchangeDifference * 100) / 100,
                        amount_currency: Math.round(lineExchangeDifference * 100) / 100,
                        amountInLine: Math.round(lineExchangeDifference * 100) / 100,
                        payment_ref: "Exchange difference for " + selectedData.payment_ref,
                        is_exchange_diff: true,
                        is_manual_suspense: false,
                        currency_id: this.companyData.currency_id,
                        company_currency_id: this.companyData.currency_id,
                    };
                }
            }

            const totalSelectedAmount = this.state.reconcileLines.reduce((sum, line) => {
                return sum + (line.amountInLine ? Math.abs(line.amountInLine) : 0);
            }, 0);

            const remainingAmount = Math.abs(SAmount) - Math.abs(totalSelectedAmount);

            if (Math.abs(lineAmount) > remainingAmount && !this.state.strikeThroughRemoved) {
                line.amountInLine = remainingAmount * (lineAmount > 0 ? 1 : -1);
                line.amount_currency = line.amountInLine * (line.amount_residual_currency / line.amount_residual);
            } else {
                line.amountInLine = lineAmount;
                line.amount_currency = line.amountInLine * (line.amount_residual_currency / line.amount_residual);
            }

            this.state.reconcileLines = exchangeDifferenceLine
                ? [...this.state.reconcileLines, line, exchangeDifferenceLine]
                : [...this.state.reconcileLines, line];
        }

        this.state.reconcileLines = [...this.state.reconcileLines];
    }

    onBatchRecordSelect(records) {
        // Filter out existing lines and add new ones
        const newLines = records.filter(record => !this.state.reconcileLines.some(line => line.id === record.id));
        const withoutSuspenseLines = this.state.reconcileLines.filter(line => !line.suspense_line_id);
        const suspenseLines = this.state.reconcileLines.filter(line => line.suspense_line_id);
        this.state.reconcileLines = [...withoutSuspenseLines, ...newLines, ...suspenseLines];
    }

    onCloseCreate() {
        this.props.toggleIsCreate(false);
        this.state.paymentRef = "";
        this.state.amount = null;
        this.state.partner = false;
        this.state.foreignCurrency = false;
        this.state.foreignAmount = null;
    }

    async fetchPartnerAccounts(selectedRecord) {
        // Fetch partner account when transaction have partner data
        if (selectedRecord?.data?.partner_id) {
            const partnerId = selectedRecord.data.partner_id[0];
            await this.orm.read(
                'res.partner',
                [partnerId],
                ['property_account_receivable_id', 'property_account_payable_id']
            ).then((partnerData) => {
                if (partnerData && partnerData.length > 0) {
                    this.state.partnerAccounts.receivable = partnerData[0].property_account_receivable_id
                    this.state.partnerAccounts.payable = partnerData[0].property_account_payable_id
                }
            })
        } else {
            await this.orm.searchRead(
                'account.journal',
                [['id', '=', this.props.list.evalContext.active_id]],
                ['suspense_account_id']
            ).then((journal) => {
                if (journal && journal.length > 0 && journal[0].suspense_account_id) {
                    this.state.partnerAccounts.suspense = journal[0].suspense_account_id
                }
            })
        }
    }

    async getCompanyData() {
        this.companies = await this.orm.searchRead(
            'res.company',
            [],
            ['currency_id',
                'expense_currency_exchange_account_id',
                'income_currency_exchange_account_id',
            ]
        );
        this.companyData = this.companies.filter(
            (company) => company.id === this.company.currentCompany?.id
        )?.[0];
    }

    async getCurrencies() {
        const currencies = await this.orm.searchRead(
            'res.currency',
            [],
            ['id', 'name', 'symbol', 'rate', 'inverse_rate'],
            {
                context: {
                    company_id: this.state.selectedJournalAccount?.company_id[0],
                },
            }
        );
        this.currencies = currencies;
    }

    async getDefaultCurrency() {
        const currency_id = this.state.defaultJournalAccount?.currency_id || this.companyData.currency_id
        this.state.currency = this.currencies.find(currency => currency.id === currency_id[0]);
    }

    async getJournalAccounts() {
        const defaultJournal = await this.orm.searchRead(
            'account.journal',
            [['id', '=', this.props.list.evalContext.active_id]],
            ['default_account_id']
        );
        if (defaultJournal && defaultJournal.length > 0 && defaultJournal[0].default_account_id) {
            this.chartOfAccounts = await this.orm.searchRead(
                'account.account',
                [],
                ['id', 'name', 'code', 'currency_id', 'company_id']
            );
            const account = await this.chartOfAccounts.find(
                (account) => account.id === defaultJournal?.[0].default_account_id?.[0]
            );
            var journalCurrency = account?.currency_id
            if (!journalCurrency){
                journalCurrency = await this.companies.find(
                    (company) => company.id === account.company_id?.[0]
                )?.currency_id
            }
            if (account) {
                this.state.defaultJournalAccount = {
                    id: account.id,
                    name: account.name,
                    code: account.code,
                    display_name: `${account.code} ${account.name}`,
                    currency_id: journalCurrency,
                    company_id: account.company_id,
                };
                this.state.selectedJournalAccount = this.state.defaultJournalAccount
            }
        }
    }

    async checkWriteOffRule() {
        try {
            const journalId = this.props.list.evalContext.active_id;
            const domain = [['rule_type', '=', 'writeoff_button']];
            if (journalId) {
                domain.push('|', ['match_journal_ids', '=', false], ['match_journal_ids', 'in', [journalId]]);
            }
            const reconcileModels = await this.orm.searchRead(
                'account.reconcile.model',
                domain,
                ['id', 'name']
            );
            this.state.writeOffButtons = reconcileModels;
        } catch (error) {
            console.error("Error checking write-off rules:", error);
            this.state.isWriteOffActive = false;
        }
    }

    async validateLines() {
        // Method to reconcile the selected entries present in reconcileLines
        const moveLines = this.state.reconcileLines.map(line => ({
            id: line.id,
            account_id: line.account_id[0], // Ensure account_id is passed as [id, name] or integer
            amount_residual: line.amountInLine || line.amount_residual,
            move_id: line.move_id?.[0], // Optional: Only for invoice/bill lines
            partner_id: line.partner_id?.[0], // Partner ID for partner accounts
            name: line.move_id?.[1] || line.name || this.state.selectedRecord.data.payment_ref,
            move_type: line.move_type,
            amount_formatted: line.amount_formatted || '',
            foreign_currency_id: line.foreign_currency_id?.[0] || null,
            currency_id: line.currency_id?.[0] || this.companyData.currency_id[0],
            amount_currency: line.amount_currency || line.amountInLine || line.amount_residual,
        })).filter(line => line.id !== undefined);
        const counterParts = this.state.reconcileLines.filter(line => !line.id)

        const res = await this.orm.call(
            'account.bank.statement.line',
            'validate_transaction',
            [this.state.selectedRecord.data.id],
            {line_ids: moveLines, counter_part_lines: counterParts}
        ).then(async (res) => {
            await this.orm.write('account.bank.statement.line', [res], {
                reconcile_data_json: {
                    "data": this.state.reconcileLines,
                    reconcile_session_data: false
                }
            })
        })

        // Trigger UI updates
        this.env.bus.trigger("validate-lines");
        this.notificationService.add("Record has been reconciled ", {type: "success"});
    }

    getCurrentDate() {
        return luxon.DateTime.now();
    }

    onDateChange(date) {
        this.state.date = date;
    }

    async onSaveRecord() {
        const activeId = this.actionService.currentController?.action?.context?.active_id;

        if (!this.state.paymentRef || !this.state.amount || this.state.amount == 0) {
            this.state.showPaymentRefError = true;
            return;
        }

        let partnerId = this.state.partner ? this.state.partner.id : false;

        if (!partnerId && this.state.selectedRecord?.data?.payment_ref) {
            const paymentRef = this.state.paymentRef;
            const partnerMapping = await this.orm.searchRead(
                "account.reconcile.model.partner.mapping",
                [["payment_ref_regex", "=", paymentRef]],
                ["partner_id"]
            );

            if (partnerMapping.length > 0 && partnerMapping[0]?.partner_id) {
                partnerId = partnerMapping[0].partner_id[0];
            }
        }

        await this.orm.create("account.bank.statement.line", [{
            partner_id: partnerId,
            payment_ref: this.state.paymentRef,
            amount: this.state.amount,
            journal_id: activeId,
            date: (this.state.date && typeof this.state.date.toISODate === "function")
                ? this.state.date.toISODate()
                : this.getCurrentDate()?.toISODate(),
            amount_currency: this.state.foreignAmount,
            foreign_currency_id: this.state.foreignCurrency?.id,
        }]);

        this.env.searchModel._notify();
        this.props.toggleIsCreate(false);
        this.state.paymentRef = "";
        this.state.amount = null;
        this.state.partner = false;
        this.state.foreignCurrency = false;
        this.state.foreignAmount = null;
        this.action.doAction('soft_reload');
    }

    get noteProps() {
        return {
            pages: this.pages,
            defaultPage: this.state.defaultPage,
            onPageUpdate: this.onPageUpdate.bind(this),
        }
    }

    onPageUpdate(page) {
        this.state.defaultPage = page;
    }

    get pages() {
        const isReconciled = this.state.selectedRecord?.data.is_reconciled;
        if (!this.state.selectedJournalAccount?.company_id) return []
        const pages = [
            {
                id: "match_e_entries",
                Component: ViewWrapper,
                name: "matchExistingEntries",
                title: "Match Existing Entries",
                props: {
                    resModel: "account.move.line",
                    selectedRecord: this.state.selectedRecord,
                    onRecordSelect: this.onRecordSelect,
                    companyId: this.state.selectedJournalAccount.company_id[0],
                },
            },
            {
                id: "batch_payment",
                Component: BatchPayments,
                name: "batchPayment",
                title: "Batch Payment",
                props: {
                    resModel: "batch.payment",
                    onBatchRecordSelect: this.onBatchRecordSelect,
                    companyId: this.state.selectedJournalAccount.company_id[0],
                },
            },
            {
                id: "manual_operation",
                Component: ManualOperation,
                name: "manualOperation",
                title: "Manual Operation",
                props: {
                    lineData: this.state.selectedLine,
                    reconcileLines: this.state.reconcileLines,
                    lineIndex: this.state.selectedLineIndex,
                    partnerAccounts: this.state.partnerAccounts,
                    amount: this.state.selectedRecord?.data.amount / this.state.selectedRecord?.data.currency_rate,
                    isReconciled: this.state.selectedRecord?.data.is_reconciled,
                    companyCurrency: this.state.selectedJournalAccount.currency_id || this.companyData.currency_id,
                    currencies: this.currencies,
                    onLineChange: (index, newData) => {
                        const updatedLines = [...this.state.reconcileLines];
                        updatedLines[index] = {...updatedLines[index], ...newData};
                        this.state.reconcileLines = updatedLines;
                        this.computeSuspenseAccount();

                        // Handle partner/tax line updates
                        const updatedLine = updatedLines[index];
                        if (updatedLine.suspense_line_id) {
                            this.state.reconcileLines.forEach((line) => {
                                if (line.suspense_line_id === updatedLine.suspense_line_id) {
                                    // Update partner_id for tax lines if parent line is updated
                                    if (line.tax_id && updatedLine.partner_id) {
                                        line.partner_id = updatedLine.partner_id;
                                    }
                                    // Update payment_ref for all related lines
                                    if (updatedLine.payment_ref) {
                                        line.payment_ref = updatedLine.payment_ref;
                                    }
                                }
                            });
                        }
                    },
                    onBankLineChange: (newData) => {
                        this.state.selectedRecord.data = {...this.state.selectedRecord.data, ...newData}
                        if (newData.foreign_currency_id) {
                            newData.foreign_currency_id = newData.foreign_currency_id[0]
                        }
                        this.orm.call("account.bank.statement.line", "update_statement_line_fields", [this.state.selectedRecord.data.id], {fields_data: newData})
                        this.computeSuspenseAccount();
                    },
                    onTaxUpdate: (taxes, counterpartId, suspenseLineId) => {
                        const taxIds = taxes.map(tax => tax.id);
                        const identifier = counterpartId ? 'counterpart_id' : 'suspense_line_id';
                        const idValue = counterpartId || suspenseLineId;

                        const handleTaxUpdate = (parentLine) => {
                            if (!parentLine.amount_before_tax) {
                                parentLine.amount_before_tax = parentLine.amount_residual;
                            }

                            // Remove existing tax lines
                            this.state.reconcileLines = this.state.reconcileLines.filter(
                                line => !(line[identifier] === idValue && line.tax_id)
                            );

                            if (taxIds.length > 0) {
                                const totalTaxRate = taxes.reduce((sum, tax) => sum + (tax.amount / 100), 0);
                                const baseAmount = Math.round((parentLine.amount_before_tax / (1 + totalTaxRate)) * 100) / 100;

                                taxes.forEach(tax => {
                                    const taxAmount = Math.round((baseAmount * (tax.amount / 100)) * 100) / 100;
                                    const newTaxLine = {
                                        [identifier]: idValue,
                                        tax_id: tax.id,
                                        amount_residual: taxAmount,
                                        account_id: tax.account_id,
                                        partner_id: parentLine.partner_id,
                                        [identifier === 'counterpart_id' ? 'is_counterpart' : 'is_suspense']: true,
                                        payment_ref: parentLine.payment_ref,
                                        tax_amount: tax.amount
                                    };

                                    this.state.reconcileLines.push(newTaxLine);
                                });

                                const totalTaxAmount = baseAmount * totalTaxRate;
                                parentLine.amount_residual = baseAmount;
                            } else {
                                parentLine.amount_residual = parentLine.amount_before_tax;
                            }
                        };

                        const parentLine = this.state.reconcileLines.find(
                            line => line[identifier] === idValue && !line.tax_id
                        );

                        if (parentLine) {
                            handleTaxUpdate(parentLine);
                        }
                    }
                },
            },
            {
                id: "chatter",
                Component: Chatter,
                name: "discuss",
                title: "Discuss",
                props: {
                    threadModel: "account.bank.statement.line",
                    threadId: this.state.selectedRecord?.data.id,
                },
            },
        ];
        return isReconciled ? pages.filter(page => page.id === "manual_operation" || page.id === "chatter") : pages;
    }

    async onReset() {
        await this.orm.call('account.bank.statement.line', 'action_undo_reconciliation', [[this.state.selectedRecord.resId]]).then(() => {
            this.env.searchModel._notify()
            this.notificationService.add("Record has been reset to unreconciled ", { type: "success" });
            this.env.bus.trigger("validate-lines");
        });
    }

    async onMarkToCheck(resId) {
        if (this.state.selectedRecord) {
            try {
                await this.orm.call('account.bank.statement.line', 'toggle_to_check', [[this.state.selectedRecord.resId]]);
                this.state.selectedRecord.data.to_check = true;
                this.state.showDefaultButtons = false;
            } catch (error) {
                console.error("Error marking as 'To Check':", error);
            }
        }
    }

    async onSetAsChecked() {
        if (this.state.selectedRecord) {
            try {
                await this.orm.call('account.bank.statement.line', 'toggle_to_check', [[this.state.selectedRecord.resId]]);
                this.state.selectedRecord.data.to_check = false;
                this.state.showDefaultButtons = true;
            } catch (error) {
                console.error("Error marking as 'Set as Checked':", error);
            }
        }
    }

    get selectedData() {
        return this.state.selectedRecord?.data ?? false;
    }

    async onClickLines(selectedRecord) {
        try {
            await this.orm.write('account.bank.statement.line', [this.state.selectedRecord.data.id], {reconcile_session_data: {data: false}})
        } finally {
            const {resModel, resId} = selectedRecord;
            this.state.isLoading = true;
            try {
                await this.fetchPartnerAccounts(selectedRecord).then(async () => {
                    this.state.isWriteOffActive = false;
                    this.state.selectedRecord = selectedRecord;
                    const recordData = await this.orm.read(resModel, [resId], ['is_reconciled']);
                    if (recordData && recordData.length > 0) {
                        this.state.isReconciled = recordData[0].is_reconciled;
                    }
                    await this.addSuggestedEntries();
                });
                if (this.state.selectedRecord) {
                    const reconcileData = this.state.selectedRecord.data.reconcile_session_data?.data
                    if (reconcileData) {
                        this.state.reconcileLines = reconcileData.reconcileLines
                    }
                }
            } finally {
                this.state.isLoading = false;
                this.state.selectedLine = this.state.selectedRecord?.data
                this.state.selectedLine.isBankStatementLine = true
            }
        }
    }

    onLineClick(line) {
        const index = this.state.reconcileLines.findIndex(obj => Object.is(obj, line));
        this.highlightSelectedRow(index)
        if (index !== -1) {
            this.state.selectedLine = line;
            this.state.selectedLineIndex = index;
        } else {
            this.state.selectedLine = this.state.selectedRecord?.data
            this.state.selectedLine.isBankStatementLine = true
        }
    }

    async addSuggestedEntries() {
        this.state.isLoading = true;
        const { resModel, resId } = this.state.selectedRecord;
        const selectedData = this.state.selectedRecord?.data;
        const SAmount = selectedData?.amount / selectedData?.currency_rate;
        this.state.reconcileLines = [];

        try {
            await this.orm.call(resModel, "get_match_invoice", [resId]).then((response) => {
                if (response?.length > 0) {
                    const newLines = response[0];
                    if (!newLines) return;
                    const updatedReconcileLines = [];
                    let totalAmount = 0;
                    let totalExchangeDifference = 0;
                    const isCounterpart = newLines.some((line) => line.is_counterpart)

                    newLines.forEach((newLine) => {
                        if (totalAmount < Math.abs(SAmount) || isCounterpart) {
                            const lineExchangeDifference = this.computeExchangeDifference(newLine);
                            totalExchangeDifference += lineExchangeDifference;

                            const lineAmount = newLine.amount_residual;
                            const remainingAmount = Math.abs(SAmount) - totalAmount - lineExchangeDifference;
                            if (!isCounterpart) {

                                if (Math.abs(lineAmount) > remainingAmount) {
                                    newLine.amountInLine = remainingAmount * (lineAmount > 0 ? 1 : -1);
                                    newLine.amount_currency = newLine.amountInLine * (newLine.amount_residual_currency / newLine.amount_residual);
                                } else {
                                    newLine.amountInLine = lineAmount;
                                    newLine.amount_currency = newLine.amountInLine * (newLine.amount_residual_currency / newLine.amount_residual);
                                }
                            }
                            totalAmount += Math.abs(newLine.amountInLine);
                            updatedReconcileLines.push(newLine);
                            this.state.counterpartLines = [...this.state.counterpartLines, newLine];
                        }
                    });

                    if (totalExchangeDifference !== 0) {
                        const exchangeDifferenceLine = {
                            account_id: (
                                totalExchangeDifference < 0
                                    ? this.companyData.expense_currency_exchange_account_id
                                    : this.companyData.income_currency_exchange_account_id
                            ),
                            amount_residual: Math.round(totalExchangeDifference * 100) / 100,
                            amount_currency: Math.round(totalExchangeDifference * 100) / 100,
                            amountInLine: Math.round(totalExchangeDifference * 100) / 100,
                            payment_ref: "Exchange difference for " + selectedData.payment_ref,
                            is_exchange_diff: true,
                            is_manual_suspense: false,
                            currency_id: this.companyData.currency_id,
                            company_currency_id: this.companyData.currency_id,
                        };
                        updatedReconcileLines.push(exchangeDifferenceLine)
                    }

                    this.state.reconcileLines = updatedReconcileLines;
                }
            });
        } finally {
            this.state.isLoading = false; // Set loading to false when done
        }
    }

    async onWriteOff(modelId) {
        try {
            this.state.isWriteOffActive = true;
            let existingButtonLines = this.state.reconcileLines.filter(line => line.is_button)
            if (existingButtonLines.length) {
                this.state.reconcileLines = this.state.reconcileLines.filter(line => !existingButtonLines.includes(line))
            } else {
                const totalMatched = this.state.reconcileLines.reduce((sum, line) => sum + (line.amountInLine || line.amount_residual || 0), 0);
                const suspenseLines = this.state.reconcileLines.filter(line => line.suspense_line_id);
                await this.orm.call('account.bank.statement.line', 'button_counterpart_entries', [this.state.selectedRecord.resId], {
                    model: modelId,
                    total_matched: totalMatched,
                    suspense_amounts: suspenseLines.map(line => line.amount_residual || line.amountInLine || 0), // pass amounts
                }).then((res) => {
                    if (res.length) {
                        this.state.reconcileLines = this.state.reconcileLines.filter(line => !line.is_button)
                        const newEntries = res.map(entry => ({...entry, is_counterpart: true}));
                        const withoutSuspenseLines = this.state.reconcileLines.filter(line => !line.suspense_line_id);
                        this.state.reconcileLines = [...withoutSuspenseLines, ...newEntries, ...suspenseLines];
                    }
                })
            }
            this.computeSuspenseAccount()
        } catch (error) {
            console.error("Error in write-off processing:", error);
        }
    }

    onDeleteLine(line) {
        const index = this.state.reconcileLines.findIndex(obj => Object.is(obj, line));
        if (index !== -1) {
            let linesToRemove = [index];

            // If line is counterpart or suspense, find and remove related tax lines
            if (line.counterpart_id || line.suspense_line_id) {
                const identifier = line.counterpart_id ? 'counterpart_id' : 'suspense_line_id';
                const idValue = line.counterpart_id || line.suspense_line_id;

                this.state.reconcileLines.forEach((l, i) => {
                    if (l[identifier] === idValue && l.tax_id && i !== index) {
                        linesToRemove.push(i);
                    }
                });
            }

            // Sort in descending order to avoid index shifting during deletion
            linesToRemove.sort((a, b) => b - a);

            let updatedLines = [...this.state.reconcileLines];
            linesToRemove.forEach(i => {
                updatedLines = [
                    ...updatedLines.slice(0, i),
                    ...updatedLines.slice(i + 1)
                ];
            });

            this.state.reconcileLines = updatedLines;
            this.computeSuspenseAccount();
        }
    }

    async openRecord(id) {
        const reconcileData = {
            reconcileLines: this.state.reconcileLines,
        }
        await this.orm.write('account.bank.statement.line', [this.state.selectedRecord.data.id], { reconcile_session_data: { data: reconcileData } })
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            target: 'current',
            res_id: id,
            res_model: "account.move",
            views: [[false, 'form']],
        })
    }

    highlightSelectedRow(index) {
        const allRows = document.querySelectorAll('tr');
        allRows.forEach((row, i) => {
            if (i === index + 2) {
                row.classList.add('highlight');
            } else {
                row.classList.remove('highlight');
            }
        });
    }
}

ReconcileRenderer.template = "ReconcileRenderer";
ReconcileRenderer.props = {
    list: {
        type: Object,
        optional: true
    },
    isCreate: {
        type: Boolean,
        optional: true
    },
    toggleIsCreate: {
        type: Function,
        optional: true
    },
    createNew: {
        type: Function,
        optional: true
    },
    activeActions: {
        type: Object,
        optional: true
    },
    archInfo: {
        type: Object,
        optional: true
    },
    allowSelectors: {
        type: Boolean,
        optional: true
    },
    onOpenFormView: {
        type: Function,
        optional: true
    },
    openRecord: {
        type: Function,
        optional: true
    },
    noContentHelp: {
        type: String,
        optional: true
    },
    onAdd: {
        type: Function,
        optional: true
    },
    onOptionalFieldsChanged: {
        type: Function,
        optional: true
    },
    evalViewModifier: {
        type: Function,
        optional: true
    },
}

ReconcileRenderer.components = {
    ReconcileLines,
    Notebook,
    ManualOperation,
    BatchPayments,
    Many2XAutocomplete,
    DateTimeInput,
    Dropdown,
    DropdownItem,
};
