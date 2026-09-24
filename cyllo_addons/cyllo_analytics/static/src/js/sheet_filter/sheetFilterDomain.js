/* @odoo-module */
import { Component, useState, useRef, useEffect, onWillStart } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { SheetDomainSelector } from "./sheetDomainSelector";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { getPsqlOperatorsAndValues } from "./fieldDef";
import { parseQueryToDomain } from "./queryParserToDomain";

export class SheetFilterDomain extends Component {
    static template = "SheetFilterDomain"
    static components = { Dialog, SheetDomainSelector, Dropdown, DropdownItem }

    setup() {
        this.root = useRef("root")
        this.state = useState({
            name: this.props.where.name || "",
            showWarn: false,
            domains: this.props.where?.domain_py_expression || [],
            query: this.props.where?.domain || "",
            domainWarn: false,
            domainNoEdit: false,
        })
        useEffect(() => {
            this.state.domainWarn = false
        }, () => [...this.state.domains]);

        onWillStart(this.parseDomain)
    }

    parseDomain() {
        if (this.state.query && !this.state.domains.length) {
            const tables = this.props.models.map(item => {
                return {
                    fields: item.fields,
                    table: item.table,
                    model: item.model,
                    modelName: item.name
                }
            })
            const parsed = parseQueryToDomain(this.state.query, tables)
            if (!parsed.error) {
                this.state.domains = parsed.domains
                this.state.domainNoEdit = false
            } else {
                this.state.domainNoEdit = true
            }
        }
    }

    addModel(model) {
        this.state.domains.push({ table: model.table, model: model.model, modelName: model.name, domain: "[]" })
    }

    onModelSelect(ev) {
        const index = ev.target.value;
        if (index !== "") {
            const model = this.resModels[index];
            if (model) {
                this.addModel(model);
            }
            ev.target.value = "";
        }
    }

    getOrWhereClause(domains) {
        const conditions = [];
        let isValidDomain = domains.length;
        for (const rec of domains) {
            let modifiedArray = JSON.parse(rec.domain.replace(/\(/g, '[').replace(/\)/g, ']').replace(/True/g, 'true').replace(/False/g, 'false'));
            modifiedArray = modifiedArray.filter(item => !["|", "&"].includes(item))
            const model = this.props.models.find(item => item.model === rec.model)
            const { table } = model
            if (isValidDomain) {
                isValidDomain = modifiedArray.length
            }
            modifiedArray.forEach(item => {
                const [lhs, opr, rhs] = item;
                // Check if this is a virtual preset field
                const virtualField = (this.props.fields || []).find(f => f.name === lhs && f.is_preset);

                let fieldExpr;
                let fieldType;

                if (virtualField) {
                    fieldExpr = `(${virtualField.raw_formula})`;
                    fieldType = virtualField.type;
                } else {
                    const field = model.fields[lhs];
                    fieldExpr = `${table}.${lhs}`;
                    fieldType = field.type;
                }

                const [possibleVals, groupRhs, isvalid] = getPsqlOperatorsAndValues({
                    type: fieldType,
                    operator: opr,
                    value: rhs
                });

                // Replace {field} placeholder for period operators that reference field twice
                const resolvedRhs = groupRhs.replace(/\{field\}/g, fieldExpr);
                conditions.push(`${fieldExpr} ${resolvedRhs}`);
                if (isValidDomain) {
                    isValidDomain = Boolean(isvalid)
                }
            });
        }
        return [conditions.join(' OR '), isValidDomain]
    }

    get warnClass() {
        return this.state.showWarn ? this.state.name.length ? "" : "show-danger-input" : ""
    }

    handleSaveFilter() {
        if (!this.state.name.length) {
            this.root.el.querySelector(".filter_name_input").focus();
            this.state.showWarn = true
            setTimeout(() => {
                if (owl.status(this) !== "destroyed") {
                    this.state.showWarn = false
                }
            }, 5000)
            return
        }
        const [query, isValidDomain] = this.getOrWhereClause(this.state.domains)
        if (!isValidDomain) {
            this.state.domainWarn = true
            return;
        } else {
            this.state.domainWarn = false
        }
        this.state.query = query
        const data = this.props.where.id ? {
            ...this.props.where,
            domain: this.state.query,
            domain_py_expression: this.state.domains,
        } : {
            id: new Date().toISOString(), //Temp id
            active: this.props.where.active || true,
            domain: this.state.query,
            name: this.state.name,
            domain_py_expression: this.state.domains,
        }
        data.isEdit = this.props.isEdit
        this.props.confirm(data)
        this.props.close()
    }

    get resModels() {
        const stateModels = new Set(this.state.domains.map(item => item.model));
        return this.props.models.filter(model => !stateModels.has(model.model));
    }


    getDomainSelectorProps(model) {
        return {
            readonly: false,
            isDebugMode: false,
            resModel: model.model,
            modelName: model.modelName,
            defaultConnector: "|",
            domain: model.domain,
            handleDeleteDomain: this.handleDeleteDomain.bind(this),
            update: (domain) => {
                model.domain = domain;
                const [query, isValidDomain] = this.getOrWhereClause(this.state.domains)
                this.state.domainWarn = !isValidDomain
            }
        };
    }
    handleDeleteDomain(model) {
        this.state.domains = this.state.domains.filter(item => item.model !== model)
    }
}