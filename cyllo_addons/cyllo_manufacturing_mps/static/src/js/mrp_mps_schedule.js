/** @odoo-module */

import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { ControlPanel } from "@web/search/control_panel/control_panel";
import { Component, useState } from "@odoo/owl";
import {_t} from "@web/core/l10n/translation";


export class MPSClientAction extends Component {
    async setup() {
        this.actionService = useService("action");
        this.orm = useService("orm");
        this.dialog = useService("dialog");

        this.state = useState({
            period: "month",
            search: "",
            columns: [],
            products: [],
            expandedProducts: {},
        });

        this.productMap = new Map();
        await this.fetchConfig();
        await this.generateColumns();
    }

    async fetchConfig() {
        try {
            const config = await this.orm.call("mrp.mps.schedule", "get_mps_config", []);
            if (config?.period) {
                this.state.period = config.period;
            }
        } catch (error) {
            this.dialog.add(ConfirmationDialog, {
                title: _t("Error"),
                body: "Failed to load configuration."
            });
        }
    }

    async loadData() {
        const data = await this.orm.call("mrp.mps.schedule", "get_product_data", []);
        const firstColLabel = this.state.columns[0]?.label;

        this.state.products = data.map((product) => {
            const demand = product.saved_demand || {};
            const confirmedSales = parseFloat(product.outgoing_qty) || 0;

            if (Object.keys(demand).length === 0 && firstColLabel) {
                demand[firstColLabel] = confirmedSales;
            }

            return {
                ...product,
                initialStock: parseFloat(product.initialStock) || 0,
                demand,
                indirect_demand: {},
                replenishment: product.saved_replenishment || {},
                manual_replenishment: product.saved_manual_repl || {},
                stock: {},
                startingStock: {},
            };
        });

        this.productMap = new Map();
        const products = this.state.products;
        for (let i = 0; i < products.length; i++) {
            this.productMap.set(products[i].id, products[i]);
        }

        this.initializeData();
    }

    async generateColumns() {
        const today = new Date();
        const columns = [];

        for (let i = 0; i < 12; i++) {
            let label;
            const date = new Date(today);

            if (this.state.period === "month") {
                date.setMonth(today.getMonth() + i);
                label = date.toLocaleString("default", { month: "short", year: "numeric" });
            } else if (this.state.period === "week") {
                date.setDate(today.getDate() + i * 7);
                label = `W${this.getWeekNumber(date)} ${date.getFullYear()}`;
            } else if (this.state.period === "day") {
                date.setDate(today.getDate() + i);
                label = date.toLocaleDateString("en-US");
            } else {
                label = String(today.getFullYear() + i);
            }

            columns.push({ label });
        }

        this.state.columns = columns;
        await this.loadData();
    }

    initializeData() {
        const products = this.state.products;
        const columns = this.state.columns;

        for (let productIndex = 0; productIndex < products.length; productIndex++) {
            const product = products[productIndex];
            for (let columnIndex = 0; columnIndex < columns.length; columnIndex++) {
                const label = columns[columnIndex].label;
                product.demand[label] ||= 0;
                product.indirect_demand[label] ||= 0;
                product.replenishment[label] ||= 0;
                product.manual_replenishment[label] ||= false;
                product.stock[label] = 0;
                product.startingStock[label] = 0;
            }
        }
        this.computeAllStock();
    }

    computeAllStock() {
        const periodColumns = this.state.columns;
        const productList = this.state.products;

        const totalPeriods = periodColumns.length;
        const totalProducts = productList.length;

        for (let periodIndex = 0; periodIndex < totalPeriods; periodIndex++) {
            const currentPeriodLabel = periodColumns[periodIndex].label;
            const previousPeriodLabel = periodIndex === 0
                ? null
                : periodColumns[periodIndex - 1].label;

            for (let productIndex = 0; productIndex < totalProducts; productIndex++) {
                productList[productIndex].indirect_demand[currentPeriodLabel] = 0;
            }

            for (let propagationRound = 0; propagationRound < 3; propagationRound++) {
                for (let productIndex = 0; productIndex < totalProducts; productIndex++) {
                    const currentProduct = productList[productIndex];

                    const previousStockLevel = previousPeriodLabel === null
                        ? currentProduct.initialStock
                        : currentProduct.stock[previousPeriodLabel];

                    currentProduct.startingStock[currentPeriodLabel] = previousStockLevel;

                    const directDemand = currentProduct.demand[currentPeriodLabel] || 0;
                    const indirectDemand = currentProduct.indirect_demand[currentPeriodLabel] || 0;

                    const totalDemand = directDemand + indirectDemand;
                    const stockAfterDemand = previousStockLevel - totalDemand;

                    if (
                        !currentProduct.manual_replenishment[currentPeriodLabel] &&
                        currentProduct.replenishment_mode !== "never"
                    ) {
                        let suggestedReplenishmentQty = 0;

                        if (stockAfterDemand < currentProduct.target_qty) {
                            suggestedReplenishmentQty = Math.max(
                                currentProduct.min_qty,
                                currentProduct.target_qty - stockAfterDemand
                            );
                        }

                        currentProduct.replenishment[currentPeriodLabel] = suggestedReplenishmentQty;
                    }

                    const appliedReplenishmentQty = currentProduct.replenishment[currentPeriodLabel] || 0;

                    currentProduct.stock[currentPeriodLabel] = stockAfterDemand + appliedReplenishmentQty;

                    if (appliedReplenishmentQty > 0 && currentProduct.bom_components) {
                        const bomComponents = currentProduct.bom_components;

                        for (let componentIndex = 0; componentIndex < bomComponents.length; componentIndex++) {
                            const componentLine = bomComponents[componentIndex];
                            const componentProduct = this.productMap.get(componentLine.schedule_id);

                            if (componentProduct) {
                                componentProduct.indirect_demand[currentPeriodLabel] +=
                                    appliedReplenishmentQty * componentLine.qty;
                            }
                        }
                    }
                }
            }
        }

    for (let productIndex = 0; productIndex < totalProducts; productIndex++) {
        const currentProduct = productList[productIndex];

        currentProduct.has_indirect_demand = periodColumns.some(
            period => currentProduct.indirect_demand[period.label] > 0
        );
    }
}

    async onClickOrder() {
        const label = this.state.columns[0]?.label;
        const schedulesToOrder = {};
        const products = this.state.products;

        for (let i = 0; i < products.length; i++) {
            const product = products[i];
            if (product.replenishment[label] > 0) {
                schedulesToOrder[product.id] = product.replenishment[label];
            }
        }

        if (Object.keys(schedulesToOrder).length === 0) {
            return this.dialog.add(ConfirmationDialog, {
                title: _t("Warning"),
                body: "No replenishment required for the current period."
            });
        }

        const action = await this.orm.call("mrp.mps.schedule", "create_purchase_manufacture_orders", [schedulesToOrder]);
        if (action?.type) {
            this.actionService.doAction(action);
        } else {
            await this.loadData();
            this.dialog.add(ConfirmationDialog, {
                title: _t("Success"),
                body: "Replenishment order created successfully.",
            });
        }
    }

    async onClickSingleOrder(productId) {
        const currentPeriodLabel = this.state.columns[0]?.label;
        const orderPayload = {};

        const selectedProduct = this.state.products.find(
            product => product.id === productId
        );

        if (selectedProduct && selectedProduct.replenishment[currentPeriodLabel] > 0) {
            orderPayload[selectedProduct.id] =
                selectedProduct.replenishment[currentPeriodLabel];
        }

        if (Object.keys(orderPayload).length === 0) {
            return this.dialog.add(ConfirmationDialog, {
                title: _t("Warning"),
                body: "No replenishment required for this product in the current period."
            });
        }

        const actionResult = await this.orm.call(
            "mrp.mps.schedule",
            "create_purchase_manufacture_orders",
            [orderPayload]
        );

        if (actionResult?.type) {
            this.actionService.doAction(actionResult);
        } else {
            await this.loadData();
            this.dialog.add(ConfirmationDialog, {
                title: _t("Success"),
                body: "Replenishment order created successfully for the selected product.",
            });
        }
    }

    onClickAddProduct() {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "MPS Schedule",
            res_model: "mrp.mps.schedule",
            view_mode: "form",
            views: [[false, "form"]],
            target: "new",
        }, { onClose: () => this.loadData() });
    }

    openAddProductForm(resId) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "MPS Schedule",
            res_model: "mrp.mps.schedule",
            res_id: resId,
            view_mode: "form",
            views: [[false, "form"]],
            target: "new",
        }, { onClose: () => this.loadData() });
    }

    async removeProduct(id) {
        this.dialog.add(ConfirmationDialog, {
            body: "Remove this product from MPS?",
            confirm: async () => {
                await this.orm.unlink("mrp.mps.schedule", [id]);
                await this.loadData();
            },
        });
    }

    async setPeriod(period) {
        this.state.period = period;
        await this.generateColumns();
    }

    toggleProduct(id) {
        this.state.expandedProducts[id] = !this.state.expandedProducts[id];
    }

    async updateValue(product, type, key, ev) {
        const val = parseFloat(ev.target.value) || 0;
        if (type === "replenishment") {
            product.manual_replenishment[key] = ev.target.value.trim() !== "";
        }
        product[type][key] = val;
        this.computeAllStock();
        await this.orm.call("mrp.mps.schedule", "update_period_data", [
            product.id,
            product.demand,
            product.replenishment,
            product.manual_replenishment
        ]);
    }

    getWeekNumber(date) {
        const weekDate = new Date(date);
        weekDate.setHours(0,0,0,0);
        weekDate.setDate(weekDate.getDate() + 3 - ((weekDate.getDay() + 6) % 7));
        const w1 = new Date(weekDate.getFullYear(), 0, 4);
        return 1 + Math.round(((weekDate - w1) / 86400000 - 3 + ((w1.getDay() + 6) % 7)) / 7);
    }
}

MPSClientAction.template = "cyllo_manufacturing_mps.MPSClientAction";
MPSClientAction.components = { ControlPanel };
registry.category("actions").add("cyllo_manufacturing_mps.mps", MPSClientAction);
