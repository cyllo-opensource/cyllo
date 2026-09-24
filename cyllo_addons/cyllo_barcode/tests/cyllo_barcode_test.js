/** @odoo-module */
import { makeTestEnv } from '@web/../tests/helpers/mock_env';
import { registry } from "@web/core/registry";
import { click, getFixture, patchWithCleanup } from "@web/../tests/helpers/utils";
import { Component, xml } from "@odoo/owl";
import { createWebClient, doAction, getActionManagerServerData } from "@web/../tests/webclient/helpers";

let serverData;
const actionRegistry = registry.category("actions");

QUnit.module("CylloBarcode", (hooks) => {
    hooks.beforeEach(() => {
        serverData = getActionManagerServerData();
    });
    QUnit.module("Barcode Main");

    QUnit.test("Cyllo-main", async function (assert) {
        const webClient = await createWebClient({ serverData })
        const mathUtils = new MathUtils();

        assert.strictEqual(mathUtils.modulo(12, 5), 2, 'should return the modulo of 42 and 5');
        const webClient = await createWebClient({ serverData });
        await doAction(webClient, {
            name: "Dialog Test",
            target: "new",
            tag: "__test__client__action__",
            type: "ir.actions.client",
        });
        assert.containsOnce(target, ".modal .test_client_action");
        assert.strictEqual(target.querySelector(".modal-title").textContent, "Dialog Test");
    });
})

class MathUtils {
    add(a, b) {
    // Implement basic addition logic here
        return a + b;
    }

    modulo(a, b) {
    // Implement basic modulo logic here
        return a % b;
    }
}
