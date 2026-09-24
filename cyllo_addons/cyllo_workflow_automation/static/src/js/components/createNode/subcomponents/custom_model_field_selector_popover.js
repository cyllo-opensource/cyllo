/** @odoo-module */

import { ModelFieldSelectorPopover } from "@web/core/model_field_selector/model_field_selector_popover";
import {sortBy} from "@web/core/utils/arrays";
import {fuzzyLookup} from "@web/core/utils/search";

export class Page {
    constructor(resModel, fieldDefs, options = {}) {
        this.resModel = resModel;
        this.fieldDefs = fieldDefs;
        const {previousPage = null, selectedName = null, isDebugMode} = options;
        this.previousPage = previousPage;
        this.selectedName = selectedName;
        this.isDebugMode = isDebugMode;
        this.sortedFieldNames = sortBy(Object.keys(fieldDefs), (key) => fieldDefs[key].string);
        this.fieldNames = this.sortedFieldNames;
        this.query = "";
        this.focusedFieldName = null;
        this.resetFocusedFieldName();
    }
    get path() {
        const previousPath = this.previousPage?.path || "";
        if (this.selectedName) {
            if (previousPath) {
                return `${previousPath}.${this.selectedName}`;
            } else {
                return this.selectedName;
            }
        }
        return previousPath;
    }

    get selectedField() {
        return this.fieldDefs[this.selectedName];
    }

    get title() {
        const prefix = this.previousPage?.previousPage ? "... > " : "";
        const title = this.previousPage?.selectedField.string || "";
        return `${prefix}${title}`;
    }

    focus(direction) {
        if (!this.fieldNames.length) {
            return;
        }
        const index = this.fieldNames.indexOf(this.focusedFieldName);
        if (direction === "previous") {
            if (index === 0) {
                this.focusedFieldName = this.fieldNames[this.fieldNames.length - 1];
            } else {
                this.focusedFieldName = this.fieldNames[index - 1];
            }
        } else {
            if (index === this.fieldNames.length - 1) {
                this.focusedFieldName = this.fieldNames[0];
            } else {
                this.focusedFieldName = this.fieldNames[index + 1];
            }
        }
    }

    resetFocusedFieldName() {
        if (this.selectedName && this.fieldNames.includes(this.selectedName)) {
            this.focusedFieldName = this.selectedName;
        } else {
            this.focusedFieldName = this.fieldNames.length ? this.fieldNames[0] : null;
        }
    }

    searchFields(query = "") {
        this.query = query;
        this.fieldNames = this.sortedFieldNames;
        if (query) {
            this.fieldNames = fuzzyLookup(query, this.fieldNames, (key) => {
                const vals = [this.fieldDefs[key].string];
                if (this.isDebugMode) {
                    vals.push(key);
                }
                return vals;
            });
        }
        this.resetFocusedFieldName();
    }
}

export class CustomCreateModelFieldSelectorPopover extends ModelFieldSelectorPopover{
    setup(){
        super.setup();
    }

    async loadPages(resModel, path) {
        if (typeof path !== "string" || !path.length) {
            const fieldDefs = await this.fieldService.loadFields(resModel);
            return new Page(resModel, this.filter(fieldDefs, path), {
                isDebugMode: this.props.isDebugMode,
            });
        }
        const {isInvalid, modelsInfo, names} = await this.fieldService.loadPath(resModel, path);
        const reqmodel = Object.keys(modelsInfo[0].fieldDefs).reduce((acc, key) => {
            if (modelsInfo[0].fieldDefs[key].required === false && modelsInfo[0].fieldDefs[key].depends.length === 0) {
                acc[key] = modelsInfo[0].fieldDefs[key];
            }
            return acc;
        }, {});
        switch (isInvalid) {
            case "model":
                throw new Error(`Invalid model name: ${resModel}`);
            case "path": {
                const {resModel, fieldDefs} = modelsInfo[0];
                return new Page(resModel, this.filter(fieldDefs, path), {
                    selectedName: path,
                    isDebugMode: this.props.isDebugMode,
                });
            }
            default: {
                let page = null;
                for (let index = 0; index < names.length; index++) {
                    const name = names[index];
                    const {resModel, fieldDefs} = modelsInfo[index];
                    page = new Page(resModel, this.filter(fieldDefs, path), {
                        previousPage: page,
                        selectedName: name,
                        isDebugMode: this.props.isDebugMode,
                    });
                }
                return page;
            }
        }
    }
}
