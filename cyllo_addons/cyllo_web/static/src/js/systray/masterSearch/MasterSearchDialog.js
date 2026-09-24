/** @odoo-module **/
import {Component, onMounted, useEffect, useExternalListener, useRef, useState} from "@odoo/owl";
import {_t} from "@web/core/l10n/translation";
import {Dialog} from "@web/core/dialog/dialog";
import {useAutofocus, useOwnedDialogs, useService} from "@web/core/utils/hooks";
import {SelectCreateDialog} from "@web/views/view_dialogs/select_create_dialog";


export class MasterSearchDialog extends Component {

    setup() {
        // Set up the initial state and services.
        this.state = useState({
            focusedIndex: 0,
            query: "",
            isSearchVisible: false, // Add a state variable to control visibility
        });
        this.page = 1
        this.orm = useService("orm");
        this.inputRef = !this.props.autofocus ? useRef("autofocus") : useAutofocus();
        this.items = useState({
            data: [],
            query: ""
        });
        this.loadMoreState = useState({
            value: true
        });
        this.rpc = useService("rpc");
        this.company = useService("company");
        this.actionService = useService("action");
        this.dialogService = useService("dialog")
        useExternalListener(window, "click", this.onWindowClick);
        useExternalListener(document, "keydown", this.onKeyDown);
        this.addDialog = useOwnedDialogs();
        this.nextItemId = 1;
        this.canClose = true
        onMounted(() => {
            this.inputRef.el.focus();
        });
        useEffect(() => {
            this.page = 1
            this.computeState()
        }, () => [this.items.query])
    }

    selectCreate({domain, context, filters, title, resModel, onSelected, onUnselect}) {
        this.canClose = false
        const activeActions = {}
        this.addDialog(SelectCreateDialog, {
            title: title || _t("Select records"),
            noCreate: !activeActions.create,
            multiSelect: "link" in activeActions ? activeActions.link : false, // LPE Fixme
            resModel,
            context,
            domain,
            onSelected,
            onCreateEdit: () => {
            },
            dynamicFilters: filters,
            onUnselect,
        }, {
            onClose: () => {
                this.canClose = true
            }
        });
    }

    onKeyDown(ev) {
        if (ev.key === 'Escape') {
            this.onWindowClick(ev)
        }
    }

    toggleSearchVisibility() {
        // Toggle the visibility of the search bar.
        this.state.isSearchVisible = !this.state.isSearchVisible;
    }

    selectItem(item) {
        this.props.close()
        // Handle the selection of an item in the search results.
        if (item.isChild) {
            this.state.isSearchVisible = false;
            this.actionService.doAction(
                {
                    res_model: item.model,
                    res_id: item.id,
                    target: "current",
                    type: "ir.actions.act_window",
                    views: [[false, "form"]],
                }
            );
        } else {
            this.resetState();
        }
    }


    async loadMore(content) {
        const context = {
            create: false,
            default_company_id: false,
            delete: false,
        }
        const domain = []
        let dynamicFilters = [];
        const fieldString = content['title']
        const request = this.inputRef.el.value
        const resModel = content.model
        if (request.length) {
            const nameGets = await this.orm.call(resModel, "name_search", [], {
                name: request,
                args: domain,
                operator: "ilike",
                limit: this.props.searchMoreLimit,
                context,
            });
            dynamicFilters = [
                {
                    description: _t("Quick search: %s", request),
                    domain: [["id", "in", nameGets.map((nameGet) => nameGet[0])]],
                },
            ];
        }
        const title = _t("Search: %s", fieldString);
        this.selectCreate({
            domain,
            context,
            filters: dynamicFilters,
            title,
            resModel,
            onSelected: (ev) => {
                this.actionService.doAction({
                    type: "ir.actions.act_window",
                    res_model: resModel,
                    views: [[false, "form"]],
                    view_mode: "form",
                    res_id: ev[0],
                })
            },
            onUnselect: () => {
            },
        });
    }

    async loadMoreModels() {
        this.page++
        const [result, limit] = await this.rpc("/cy/master/search", {
            query: this.items.query,
            page: this.page,
            company_ids: this.company.activeCompanyIds
        });
        this.loadMoreState.value = Boolean(limit)
        if (result.length !== 0) {
            this.items.data.push(...result);
        }
    }

    async computeState(options = {}) {
        this.state.focusedIndex = "focusedIndex" in options ? options.focusedIndex : this.state.focusedIndex;
        const [result, limit] = await this.rpc("/cy/master/search", {
            query: this.items.query,
            page: this.page,
            company_ids: this.company.activeCompanyIds
        });
        this.loadMoreState.value = Boolean(limit)
        this.items.data = result;
    }

    resetState() {
        // Reset the state of the search bar.
        this.computeState({
            focusedIndex: 0,
        });
        this.items.query = ""
        this.inputRef.el.focus();
    }

    onWindowClick(ev) {
        if (!this.canClose) return
        if (ev?.target?.className !== 'btn-close') {
            this.props.close()
            if (this.items.data.length) {
                this.resetState();
            }
        }
    }

    CreateRecord(item) {
        // Create a new record based on the item.
        this.props.close()
        this.state.isSearchVisible = false;
        this.actionService.doAction(
            {
                res_model: item.model,
                target: "current",
                type: "ir.actions.act_window",
                views: [[false, "form"]],
            },
        );
    }

    onSearchIconClick() {
        // Handle clicks on the search icon.
        this.dialogService.add(MasterSearchDialog)
        this.toggleSearchVisibility();
    }

    onCLickMasterModal(ev) {
        ev.stopPropagation()
    }

    closeSearch() {
        // Close the search bar.
        this.state.isSearchVisible = false;
    }

    onClickModel() {
        this.onWindowClick()
        this.actionService.doAction(
            {
                res_model: 'ir.model',
                name: "Models",
                target: "current",
                type: "ir.actions.act_window",
                view_mode: 'tree,form',
                views: [[false, 'list'], [false, 'form']],
            },
        );
    }

    onClickLoadMore(name) {
        const autoCompleteInput = this.inputRef.el.querySelector("input");
        return this.onSearchMore(autoCompleteInput.value);
    }

    async onSearchMore(request) {
        const {resModel, getDomain, context, fieldString} = this.props;

        const domain = getDomain();
        let dynamicFilters = [];
        if (request.length) {
            const nameGets = await this.orm.call(resModel, "name_search", [], {
                name: request,
                args: domain,
                operator: "ilike",
                limit: this.props.searchMoreLimit,
                context,
            });

            dynamicFilters = [
                {
                    description: _t("Quick search: %s", request),
                    domain: [["id", "in", nameGets.map((nameGet) => nameGet[0])]],
                },
            ];
        }

        const title = _t("Search: %s", fieldString);
        this.selectCreate({
            domain,
            context,
            filters: dynamicFilters,
            title,
        });
    }

}

MasterSearchDialog.template = "cyllo_master_search.MasterSearchDialog"
MasterSearchDialog.components = {Dialog}