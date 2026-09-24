/** @odoo-module **/

import { getFixture, patchWithCleanup, triggerEvent} from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { browser } from "@web/core/browser/browser";

let serverData;
let target;

QUnit.module("Fields", (hooks) => {
    hooks.beforeEach(() => {
        target = getFixture();
        serverData = {
            models: {
                'res.users': {
                    fields: {
                        name: { string: "Name", type: "char" },
                        check: {
                            string: "Night Mode",
                            type: "boolean", store: true,},
                    },
                    records: [
                        {
                            id: 1,
                            name: "first record",
                            check: true,
                        },
                    ],
                    onchanges: {},
                },
            },
        };
        setupViewRegistries();
        patchWithCleanup(browser, {
            setTimeout: (fn) => fn(),
        });
    });
    QUnit.module("Users field");

    QUnit.test("enabling check boolean active with to dark mode", async function (assert) {
        await makeView({
            type: "form",
            resModel: "res.users",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <field name="name"></field>
                        <field name="check"></field>
                    </sheet>
                </form>`,
            mockRPC(route, args) {
                assert.step(args.method);
            }
        });
        // blur input => should ask for confirmation if we want to create product
        await triggerEvent(target, "[name='check'] input", "blur");
        assert.verifySteps(["get_views", "onchange"]);
    });
});