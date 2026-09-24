/* @odoo-module */

import { patchBrowserNotification } from "@mail/../tests/helpers/patch_notifications";
import { start } from "@mail/../tests/helpers/test_utils";
import { click, contains } from "@web/../tests/utils";
import { getMenuItemTexts } from "@web/../tests/search/helpers";

QUnit.module("dark mode menu");

QUnit.test("should have dark mode menu button in systray", async () => {
    await start();
    await contains(".o_menu_systray i[id='fa-icon']");
    await contains(".fa-sun-o");
});

QUnit.test("rendering with dark mode", async (assert) => {
    patchBrowserNotification("default");
    await start();
    await click(".o_menu_systray i[id='fa-icon']");
    await assert.ok(getMenuItemTexts(target));
});