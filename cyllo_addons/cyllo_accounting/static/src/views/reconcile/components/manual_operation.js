/** @odoo-module */

import { Component, useState, useEffect } from "@odoo/owl";
import { Many2OneField } from "@web/views/fields/many2one/many2one_field";
import { CharField } from "@web/views/fields/char/char_field";
import { FloatField } from "@web/views/fields/float/float_field";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";
import { TagsList } from "@web/core/tags_list/tags_list";
import { useService } from "@web/core/utils/hooks";
import { Domain } from "@web/core/domain";  // Add this import

export class ManualOperation extends Component {
    static template = "cyllo_accounting.ManualOperation";
    static components = {
        Many2OneField,
        CharField,
        FloatField,
        Many2XAutocomplete,
        TagsList,
    };

    setup() {
        this.orm = useService('orm');
        this.state = useState({
            formData: {},
            taxRecords: [],
            taxIds: [],
        });

        useEffect(
            () => {
                if (this.props.lineData) {
                    const formData = { ...this.props.lineData };

                    if (formData.amount_residual !== undefined) {
                        formData.amount_residual = this.roundToTwoDecimals(formData.amount_residual);
                    }

                    if (formData.tax_ids && formData.tax_ids.length > 0) {
                        this.loadInitialTaxes(formData.tax_ids);
                    } else {
                        this.state.taxRecords = [];
                        this.state.taxIds = [];
                    }

                    this.state.formData = formData;
                }
            },
            () => [this.props.lineData]
        );
    }

    async loadInitialTaxes(taxData) {
        const taxIds = taxData.map(tax => tax.id);
        try {
            const taxes = await this.orm.read(
                'account.tax',
                taxIds,
                ['name', 'amount']
            );

            this.state.taxRecords = taxes.map(tax => ({
                id: tax.id,
                resId: tax.id,
                data: {
                    display_name: tax.name,
                    amount: tax.amount
                }
            }));

            this.state.taxIds = taxIds;
        } catch (error) {
            console.error("Failed to load tax data:", error);
            this.state.taxRecords = taxData.map(tax => ({
                id: tax.id,
                resId: tax.id,
                data: {
                    display_name: tax.name || `Tax #${tax.id}`,
                    amount: tax.amount
                }
            }));
            this.state.taxIds = taxIds;
        }
    }

    getTagProps(record) {
        return {
            id: record.id,
            resId: record.resId,
            text: record.data.display_name,
            colorIndex: record.data.color,
            onDelete: () => this.deleteTaxTag(record.id),
        };
    }

    get taxTags() {
        return this.state.taxRecords.map(record => this.getTagProps(record));
    }

    async deleteTaxTag(id) {
        this.state.taxRecords = this.state.taxRecords.filter(record => record.id !== id);
        this.state.taxIds = this.state.taxIds.filter(taxId => taxId !== id);
        await this.updateTaxes();
    }

    updatePartner(selectedPartner) {
        if (selectedPartner && selectedPartner.length > 0) {
            const partner = selectedPartner[0];
            const partnerValue = [partner.id, partner.display_name];
            this.updateField('partner_id', partnerValue);

            if ((this.props.lineData?.is_suspense || this.props.lineData?.is_computed) && !this.props.lineData?.tax_id) {
                let newAccount = this.props.lineData.account_id;
                const partnerAccounts = this.props.partnerAccounts;

                if (partnerAccounts.receivable && partnerAccounts.payable) {
                    newAccount = this.props.amount > 0 ? partnerAccounts.receivable : partnerAccounts.payable;
                }

                this.state.formData = {
                    ...this.state.formData,
                    partner_id: partnerValue,
                    account_id: newAccount
                };

                const newData = {
                    partner_id: partnerValue,
                    account_id: newAccount,
                    is_suspense: false,
                    is_computed: false
                };

                const newTaxData = {
                    partner_id: partnerValue
                }

                if (this.props.lineData.isBankStatementLine) {
                    this.props.onBankLineChange(newData);
                } else {
                    this.props.onLineChange(this.props.lineIndex, newData);
                }
            }
        } else {
            this.updateField('partner_id', null);
        }
    }

    updateAccount(account) {
        if (account && account.length > 0) {
            const partner = account[0];
            const newValue = [partner.id, partner.display_name];
            this.updateField('account_id', newValue);

            if ((this.props.lineData?.is_suspense || this.props.lineData?.is_computed) && !this.props.lineData?.tax_id) {
                const newData = {
                    account_id: newValue,
                    is_suspense: false,
                    is_computed: false,
                    is_manual_suspense: false
                };

                if (this.props.lineData.isBankStatementLine) {
                    this.props.onBankLineChange(newData);
                } else {
                    this.props.onLineChange(this.props.lineIndex, newData);
                }
            }

            const suspenseAccount = this.props.partnerAccounts.suspense;
            if (suspenseAccount && newValue.length && suspenseAccount[0] === newValue[0]) {
                const suspenseData = {
                    account_id: newValue,
                    is_suspense: true,
                    is_computed: true,
                    is_manual_suspense: true
                };

                if (this.props.lineData.isBankStatementLine) {
                    this.props.onBankLineChange(suspenseData);
                } else {
                    this.props.onLineChange(this.props.lineIndex, suspenseData);
                }
            }
        } else {
            this.updateField('account_id', null);
        }
    }

    updateField(field, value) {
        if (field === 'amount_residual') {
            this.state.formData['amount_currency'] = (value * (
                this.props.lineData.currency_rate || this.props.currencies?.find(
                    (res) => res.id === this.props.lineData.currency_id?.[0]
                )?.rate || 1
            ));
            this.state.formData['amount_residual_currency'] = this.state.formData['amount_currency'];
            value = this.roundToTwoDecimals(value);
            this.state.formData['amountInLine'] = value;

            if (this.props.lineData?.is_suspense) {
                const bankAmount = this.props.amount;
                const otherLines = this.props.reconcileLines.filter(line =>
                    !line.is_suspense || line.is_manual_suspense
                );
                const totalOtherAmount = otherLines.reduce((sum, line) => {
                    return sum + (line.amountInLine || line.amount_residual || 0);
                }, 0).toFixed(2);

                const residual = bankAmount - totalOtherAmount;

                if (Math.abs(value + residual) < 0.01) {
                    this.state.formData.is_manual_suspense = false;
                    this.state.formData.is_suspense = true;
                    this.state.formData.is_computed = true;
                } else {
                    this.state.formData.is_manual_suspense = true;
                    this.state.formData.is_suspense = false;
                    this.state.formData.is_computed = false;
                }
            }
        }

        this.state.formData[field] = value;
        if (this.props.lineIndex !== -1 && this.props.onLineChange) {
            if (this.state.formData.isBankStatementLine === true) {
                let dataSet = {[field]: value}
                if (field === 'amount') {
                    dataSet.amount_in_base = value / this.props.lineData.currency_rate
                    this.state.formData['amount_in_base'] = dataSet.amount_in_base;
                }
                if (field === 'amount_in_base') {
                    dataSet.amount = value * this.props.lineData.currency_rate
                    this.state.formData['amount'] = dataSet.amount;
                }
                if (field === 'foreign_currency_id') {
                    if (!value){
                        dataSet.foreign_currency_id = false;
                        dataSet.foreign_currency_rate = 0;
                        dataSet.amount_currency = 0;
                        this.state.formData['amount_currency'] = 0;
                    } else {
                        dataSet.foreign_currency_id = [value.id, value.display_name];
                        dataSet.foreign_currency_rate = this.props.currencies?.find(currency => currency.id === value.id)?.rate
                        dataSet.amount_currency = this.props.lineData.amount_in_base * dataSet.foreign_currency_rate || 0;
                        this.state.formData['foreign_currency_id'] = [value.id, value.display_name]
                        this.state.formData['amount_currency'] = dataSet.amount_currency
                    }
                }
                if (field === 'amount_currency') {
                    dataSet.amount_currency = value;
                    dataSet.foreign_currency_rate = value / this.props.lineData.amount_in_base;
                    this.state.formData['amount_currency'] = dataSet.amount_currency
                }
                this.props.onBankLineChange(dataSet)
            }
            else {
                const newData = {
                    ...this.state.formData,
                    [field]: value
                };
                if (field === 'amount_residual') {
                    newData.amountInLine = value;
                }
                if (field === 'payment_ref') {
                    newData.payment_ref = value;
                }
                this.props.onLineChange(this.props.lineIndex, newData);
            }
        }
    }

    async updateTaxes(selectedRecords = []) {
        // Add new records if provided
        if (selectedRecords.length > 0) {
            const newTaxIds = selectedRecords.map(record => record.id);
            const existingIds = this.state.taxIds;
            const uniqueNewIds = newTaxIds.filter(id => !existingIds.includes(id));

            if (uniqueNewIds.length > 0) {
                try {
                    const taxes = await this.orm.read(
                        'account.tax',
                        uniqueNewIds,
                        ['name', 'amount', 'invoice_repartition_line_ids']
                    );
                    for (let i = 0; i< taxes.length; i++) {
                        const repartitionIds = taxes[i].invoice_repartition_line_ids
                        if (repartitionIds){
                            const accountIds = await this.orm.read(
                                'account.tax.repartition.line',
                                repartitionIds,
                                ['account_id']
                            )
                            for (let j = 0;j < accountIds.length; j++) {
                                if(accountIds[j].account_id && !taxes[i].account_id) {
                                    taxes[i].account_id = accountIds[j].account_id
                                }
                            }
                        }
                    }

                    const newRecords = taxes.map(tax => ({
                        id: tax.id,
                        resId: tax.id,
                        data: {
                            display_name: tax.name,
                            amount: tax.amount,
                            account_id: tax.account_id
                        }
                    }));

                    this.state.taxRecords = [...this.state.taxRecords, ...newRecords];
                    this.state.taxIds = [...this.state.taxIds, ...uniqueNewIds];
                } catch (error) {
                    console.error("Failed to load new tax data:", error);
                }
            }
        }

        // Convert to format expected by parent component
        const taxesData = this.state.taxRecords.map(record => ({
            id: record.id,
            name: record.data.display_name,
            amount: record.data.amount,
            account_id: record.data.account_id,
            counterpart_id: this.state.formData.counterpart_id || false,
        }));

        this.updateField('tax_ids', taxesData);
        if (this.props.onTaxUpdate) {
            this.props.onTaxUpdate(taxesData, this.state.formData.counterpart_id || false, this.state.formData.suspense_line_id || false);
        }
    }

    getTaxDomain() {
        // Create domain to exclude already selected taxes
        return new Domain([["id", "not in", this.state.taxIds]]).toList();
    }

    roundToTwoDecimals(value) {
        return Math.round((value + Number.EPSILON) * 100) / 100;
    }

    formatAmount(amount) {
        if (amount === undefined || amount === null) {
            return '';
        }
        return this.roundToTwoDecimals(amount).toFixed(2);
    }
}