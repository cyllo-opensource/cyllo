/** @odoo-module **/

import { Component, useEffect, useState, onWillStart, xml } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { WithSearch } from "@web/search/with_search/with_search";
import { SearchBar } from "@web/search/search_bar/search_bar";

const SEARCH_FIELD_NAMES = ["shortdesc", "name", "category_id"];

const escapeXml = (value) =>
    String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&apos;");

class DomainWatcher extends Component {
    static template = xml`<t/>`;
    static props = ["domain", "onDomainChange"];
    setup() {
        useEffect(
            () => this.props.onDomainChange(this.props.domain),
            () => [JSON.stringify(this.props.domain)]
        );
    }
}

export class AppSearchBar extends Component {
    static template = "cyllo_web.AppSearchBar";
    static components = { WithSearch, SearchBar, DomainWatcher };
    static props = ["onDomainChange", "categories?"];

    setup() {
        this.orm = useService("orm");
        this.state = useState({ searchViewFields: null });
        onWillStart(async () => {
            this.state.searchViewFields = await this.orm.call(
                "ir.module.module",
                "fields_get",
                [SEARCH_FIELD_NAMES]
            );
        });
    }

    get searchViewArch() {
        const categoryFilters = (this.props.categories || [])
            .map(
                (categ) =>
                    `<filter name="categ_${categ.id}" string="${escapeXml(categ.name)}" domain="[('category_id', '=', ${categ.id})]"/>`
            )
            .join("");
        return `<search>
            <field name="shortdesc" string="Name"/>
            <field name="name" string="Technical Name"/>
            <field name="category_id"/>
            ${categoryFilters}
        </search>`;
    }
}
