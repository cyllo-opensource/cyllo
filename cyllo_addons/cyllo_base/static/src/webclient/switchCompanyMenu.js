/** @odoo-module **/
import {SwitchCompanyMenu} from "@web/webclient/switch_company_menu/switch_company_menu";
import {patch} from "@web/core/utils/patch";
import {useState} from "@odoo/owl";

patch(SwitchCompanyMenu.prototype, {
    setup() {
        super.setup(...arguments);
        this.available_company_ids = []   // Ids of all Companies
        Object.values(this.companyService.allowedCompanies).forEach(company => {
            this.available_company_ids.push(company.id);
        });
        this.isSelectedAllCompanies = this.available_company_ids.every((el) =>
            this.companySelector.selectedCompaniesIds.includes(el)
        );
        this.state = useState({
            companiesSelected: [],
        });
    },
    /* Handles the event when the user selects all companies. */
    onSelectAllCompanies() {
        /* If all companies are already selected, this function unselects all companies. */
        this.state.companiesSelected = this.isSelectedAllCompanies ? [this.companyService.currentCompany.id] : this.available_company_ids;
        this.isSelectedAllCompanies = !this.isSelectedAllCompanies;
        this.companyService.setCompanies(this.state.companiesSelected, "loginto");
    },
});