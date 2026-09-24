/** @odoo-module **/

import { Component, useState, useRef } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { _t } from "@web/core/l10n/translation";

export class CreateProductWizard extends Component {
    static template = "cyllo_pos.CreateProductWizard";
    static components = { Dialog };
    static props = {
        close: { type: Function, optional: true },
        title: { type: String, optional: true },
    };

    setup() {
        this.pos = usePos();
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.imageInputRef = useRef("imageInput");

        // Cyllo Color Index mapping
        this.odooColors = [
            { index: 0, hex: "#FFFFFF" }, // White/Grey
            { index: 1, hex: "#F06050" }, // Red
            { index: 2, hex: "#F4A460" }, // Orange
            { index: 3, hex: "#F7CD5B" }, // Yellow
            { index: 4, hex: "#6CC1ED" }, // Light Blue
            { index: 5, hex: "#814968" }, // Purple
            { index: 6, hex: "#EB7E7F" }, // Pink
            { index: 7, hex: "#2C8397" }, // Teal
            { index: 8, hex: "#475569" }, // Slate Blue
            { index: 9, hex: "#A65F88" }, // Magenta
            { index: 10, hex: "#5DB175" }, // Green
            { index: 11, hex: "#26B99A" }, // Cyan
        ];

        this.state = useState({
            name: "",
            barcode: "",
            trackInventory: true,
            tracking: "none", // 'none', 'lot', 'serial'
            salesPrice: 1.00,
            selectedTaxIds: [],
            posCategoryId: false,
            color: 0,
            image: false,
            imageUrl: false,
            showTaxDropdown: false,
        });
    }
    //  Returns all POS categories sorted alphabetically by their name.
    get posCategories() {
        return Object.values(this.pos.db.category_by_id).sort((categoryA, categoryB) => 
            (categoryA.name || "").localeCompare(categoryB.name || "")
        );
    }

    get inclTaxPrice() {
        let price = parseFloat(this.state.salesPrice) || 0;
        let totalTax = 0;
        for (const taxId of this.state.selectedTaxIds) {
            const tax = this.pos.taxes.find(t => t.id === taxId);
            if (tax) {
                if (tax.amount_type === "percent") {
                    if (tax.price_include) {
                        // included in price
                    } else {
                        totalTax += (price * tax.amount) / 100;
                    }
                } else if (tax.amount_type === "fixed") {
                    if (tax.price_include) {
                        // included
                    } else {
                        totalTax += tax.amount;
                    }
                }
            }
        }
        return price + totalTax;
    }

    getFormattedInclTaxPrice() {
        const symbol = this.pos.currency ? this.pos.currency.symbol : "$";
        const position = this.pos.currency ? this.pos.currency.position : "before";
        const formattedPrice = this.inclTaxPrice.toFixed(2);
        if (position === "before") {
            return `(= ${symbol} ${formattedPrice} Incl. Taxes)`;
        } else {
            return `(= ${formattedPrice} ${symbol} Incl. Taxes)`;
        }
    }

    toggleTaxDropdown() {
        this.state.showTaxDropdown = !this.state.showTaxDropdown;
    }

    toggleTax(taxId) {
        const index = this.state.selectedTaxIds.indexOf(taxId);
        if (index === -1) {
            this.state.selectedTaxIds.push(taxId);
        } else {
            this.state.selectedTaxIds.splice(index, 1);
        }
    }

    removeTax(taxId) {
        const index = this.state.selectedTaxIds.indexOf(taxId);
        if (index !== -1) {
            this.state.selectedTaxIds.splice(index, 1);
        }
    }

    getTaxName(taxId) {
        const tax = this.pos.taxes.find(t => t.id === taxId);
        return tax ? tax.name : "";
    }

    onCategoryChange(ev) {
        this.state.posCategoryId = ev.target.value ? parseInt(ev.target.value) : false;
    }

    selectColor(colorIndex) {
        this.state.color = colorIndex;
    }

    triggerImageUpload() {
        this.imageInputRef.el.click();
    }

    onImageChange(ev) {
        const file = ev.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = (e) => {
                this.state.imageUrl = e.target.result;
                // Strip metadata prefix from Data URL to get raw base64 string
                this.state.image = e.target.result.split(',')[1];
            };
            reader.readAsDataURL(file);
        }
    }

    async save() {
        if (!this.state.name.trim()) {
            this.notification.add(_t("Product name is required."), { type: "danger" });
            return;
        }

        const values = {
            name: this.state.name.trim(),
            barcode: this.state.barcode.trim() || false,
            list_price: parseFloat(this.state.salesPrice) || 0.0,
            lst_price: parseFloat(this.state.salesPrice) || 0.0,
            pos_categ_ids: this.state.posCategoryId ? [[6, 0, [this.state.posCategoryId]]] : false,
            taxes_id: [[6, 0, this.state.selectedTaxIds]],
            detailed_type: this.state.trackInventory ? 'product' : 'consu',
            tracking: this.state.trackInventory ? this.state.tracking : 'none',
            color: this.state.color,
            available_in_pos: true,
        };

        if (this.state.image) {
            values.image_1920 = this.state.image;
        }

        try {
            const productIds = await this.orm.create("product.product", [values]);
            if (productIds && productIds.length > 0) {
                // Fetch and load the created product into POS database
                await this.pos._addProducts(productIds, false);
                this.notification.add(_t("Product '%s' created successfully.", this.state.name), {
                    type: "success",
                });
                this.props.close();
            }
        } catch (error) {
            console.error("Error creating product:", error);
            this.notification.add(_t("Could not create product. Please check the fields."), {
                type: "danger",
            });
        }
    }

    discard() {
        this.props.close();
    }
}