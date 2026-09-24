/** @odoo-module **/
import { registry } from "@web/core/registry";
import { BlockUI } from "@web/core/ui/block_ui";
import { download } from "@web/core/network/download";

registry.category("ir.actions.report handlers").add("docx", async function (action) {
    if (action.report_type === 'docx') {
        // Show a blocking UI while the download is in progress
        BlockUI;
        // Trigger the download of the Docx report
	    await download({
	           url: '/docx_reports',
	           data: action.data,
	           complete: () => unblockUI,// Unblock UI when the download is complete
	           error: (error) => self.call('crash_manager', 'rpc_error', error),
	    });
    }
});