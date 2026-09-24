/** @odoo-module **/
import { FormController } from "@web/views/form/form_controller";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { useService } from '@web/core/utils/hooks';
import { onWillStart } from "@odoo/owl";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

let target;

QUnit.module("Form Controller Patch", (hooks) => {
    hooks.beforeEach(() => {
        // Setup view registries before each test
        setupViewRegistries();
        // Create a target fixture for rendering views
        target = document.createElement('div');
        document.body.appendChild(target);
    });

    hooks.afterEach(() => {
        // Remove the target fixture after each test
        document.body.removeChild(target);
    });

    QUnit.test("CreateField method should call 'orm.call' and 'env.services.action.doAction'", async function (assert) {
        // Create a fake FormController instance
        const formController = new FormController();
        await formController.CreateField();
        assert.deepEqual(doActionStub.firstCall.args[0], {
            type: 'ir.actions.act_window',
            name: _t('Field Creation'),
            res_model: "field.create",
            target: 'new',
            context: {
                'active_model': formController.props.resModel,
                'default_form_view_external_id': 'fake_external_id',
                'default_model': 'fake_model',
            },
            views: [[false, 'form']],
        }, "doAction should be called with the correct parameters");
    });

    QUnit.test("getStaticActionMenuItems method should return the correct menu items", function (assert) {
        // Create a fake FormController instance
        const formController = new FormController();
        // Mock archInfo with some activeActions
        formController.archInfo = {
            activeActions: {
                create: true,
                duplicate: true,
                delete: true,
            },
        };

        // Call the getStaticActionMenuItems method
        const menuItems = formController.getStaticActionMenuItems();
        // Assertions
        assert.ok(menuItems.archive, "archive menu item should be present");
        assert.ok(menuItems.unarchive, "unarchive menu item should be present");
        assert.ok(menuItems.duplicate, "duplicate menu item should be present");
        assert.ok(menuItems.delete, "delete menu item should be present");
        assert.ok(menuItems.Create_field, "Create_field menu item should be present");
    });
});
