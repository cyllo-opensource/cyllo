/** @odoo-module **/
import { fieldService } from "@web/core/field_service";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { registry } from "@web/core/registry";
import { Component, useState, xml } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { getFixture, makeDeferred, mount, nextTick } from "@web/../tests/helpers/utils";

const serviceRegistry = registry.category("services");

function getModelInfo(resModel) {
    return {
        resModel,
        fieldDefs: serverData.models[resModel].fields,
    };
}
function getDefinitions() {
    const records = serverData.models.species.records;
    const fieldDefs = {};
    for (const record of records) {
        for (const definition of record.definitions) {
            fieldDefs[definition.name] = {
                is_property: true,
                searchable: true,
                record_name: record.display_name,
                record_id: record.id,
                ...definition,
            };
        }
    }
    return { resModel: "*", fieldDefs };
}

let serverData;
QUnit.module("Field Service Test", {
    async beforeEach() {
        serverData = {
            models: {
                fieldService: {
                    fields: {
                        id: { string: "ID", type: "integer" },
                        display_name: { string: "Display Name", type: "char" },
                        name: { string: "Name", type: "char", default: "name" },
                        write_date: { string: "Last Modified on", type: "datetime" },
                        age: { type: "integer", string: "Age" },
                        location_id: { type: "many2one", string: "Location", relation: "location" },
                        species: { type: "many2one", string: "Species", relation: "species" },
                        property_field: {
                            string: "Properties",
                            type: "properties",
                            definition_record: "species",
                            definition_record_field: "definitions",
                        },
                    },
                },
                location: {
                    fields: {
                        id: { string: "ID", type: "integer" },
                        display_name: { string: "Display Name", type: "char" },
                        name: { string: "Name", type: "char", default: "name" },
                        write_date: { string: "Last Modified on", type: "datetime" },
                        fieldService_ids: { type: "one2many", string: "Turtles", relation: "fieldService" },
                    },
                },
                species: {
                    fields: {
                        id: { string: "ID", type: "integer" },
                        display_name: { string: "Display Name", type: "char" },
                        name: { string: "Name", type: "char", default: "name" },
                        write_date: { string: "Last Modified on", type: "datetime" },
                        definitions: { string: "Definitions", type: "properties_definition" },
                    },
                    records: [
                        {
                            id: 1,
                            display_name: "new fieldService",
                            definitions: [
                                {
                                    name: "new_lifespans",
                                    string: "Lifespans",
                                    type: "integer",
                                },
                                {
                                    name: "location_ids",
                                    string: "Locations",
                                    type: "many2many",
                                    relation: "location",
                                },
                            ],
                        },
                        {
                            id: 2,
                            display_name: "fieldService",
                            definitions: [
                                { name: "aldabra", string: "Lifespans", type: "integer" },
                                { name: "color", string: "Color", type: "char" },
                            ],
                        },
                    ],
                },
            },
        };
        serviceRegistry.add("field", fieldService);
    },
});
QUnit.test("Load Field service data", async (assert) => {
    assert.expect(5);

    const mockRPC = (route) => {
        if (route.includes("fields_get")) {
            assert.step("fields_get");
            return Promise.reject("my little error");
        }
    };

    const env = await makeTestEnv({ serverData, mockRPC });

    try {
        await env.services.field.loadFields("take.five");
    } catch (error) {
        assert.strictEqual(error, "my little error");
    }
    try {
        await env.services.field.loadFields("take.five");
    } catch (error) {
        assert.strictEqual(error, "my little error");
    }
    assert.verifySteps(["fields_get", "fields_get"]);
});
