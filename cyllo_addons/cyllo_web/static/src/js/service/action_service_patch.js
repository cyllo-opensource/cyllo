/** @odoo-module **/

import { actionService } from "@web/webclient/actions/action_service";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

/**
 * Global Support for 'workflow' Button Type
 * 
 * This patch overrides the action service to natively support buttons with type="workflow".
 * It intercepts the doActionButton call and treats it as an 'object' type call
 * so it can trigger the custom Python methods injected by Cyllo Workflow Automation.
 */
const originalActionService = actionService;

const patchedActionService = {
    ...originalActionService,
    start(env) {
        const actionManager = originalActionService.start(env);
        const originalDoActionButton = actionManager.doActionButton;

        actionManager.doActionButton = async function (params) {
            if (params.type === "workflow") {
                try {
                    const count = await env.services.rpc("/web/dataset/call_kw", {
                        model: 'work.auto',
                        method: 'search_count',
                        args: [[
                            ['model_id.model', '=', params.resModel],
                            ['active', '=', true],
                            ['trigger_function_ids.func_name', '=', params.name]
                        ]],
                        kwargs: {},
                    });

                    if (count === 0) {
                        env.services.notification.add(_t("Workflow Not Linked"), {
                            message: _t("This button is not yet linked to any active workflow automation."),
                            type: "warning",
                        });
                        return;
                    }
                } catch (e) {
                    console.warn("Cyllo Workflow: Link validation failed (module might not be installed or access denied)", e);
                }
                params = { ...params, type: "object" };
            }
            return originalDoActionButton.call(this, params);
        };

        return actionManager;
    },
};

registry.category("services").add("action", patchedActionService, { force: true });
