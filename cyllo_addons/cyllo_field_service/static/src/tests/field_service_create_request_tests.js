/** @odoo-module */
import { getFixture } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

let makeViewParams, target;

QUnit.module("Field Service", (hooks) => {
    hooks.beforeEach(() => {
        makeViewParams = {
            type: "form",
            resModel: "field.service.request",
            serverData: {
                models: {
                    "field.service.request": {
                        fields: {
                            id: { string: "Id", type: "integer" },
                        },
                        records: [{ id: 1, display_name: "First record" }],
                    },
                },
            },
            arch: `<form><field name="display_name"/></form>`,
        };
        target = getFixture();
        setupViewRegistries();
    });
    QUnit.module("Form");
    QUnit.test("Field service form view", async function (assert) {
        await makeView(makeViewParams);
        assert.containsOnce(target, ".o_form_view");
    });
});
