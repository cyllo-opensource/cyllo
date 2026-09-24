/** @odoo-module **/

/**
 * Custom ActivityController for Odoo Studio to handle activity views.
 * Extends the default ActivityController with Studio-specific initialization.
 */
import { ActivityController } from "@mail/views/web/activity/activity_controller";
import { onWillStart,onMounted,useRef } from "@odoo/owl";
import { Layout } from "@web/search/layout";
import { useService } from "@web/core/utils/hooks";
import { serializeXML } from "@web/core/utils/xml";
import { addFieldDependencies, extractFieldsFromArchInfo } from "@web/model/relational_model/utils";


export class CylloActivityController extends ActivityController {
	setup() {
		super.setup();
		this.rpc = useService('rpc')
		this.dialogService = useService("dialog");
		onWillStart(async () => {
			if (!this.env.config.viewId) {
				await this.rpc('cyllo_studio/form/add/activity_view', {
					arch: serializeXML(this.props.arch),
					model: this.props.resModel,
				})
				await this.action.doAction('studio_reload')
			}
		})
	}
	/**
     * Returns model configuration for the activity view.
     * Extracts active fields and field definitions from archInfo.
     */
	get modelParams() {
		const { archInfo, resModel } = this.props;
		const { activeFields, fields } = extractFieldsFromArchInfo(archInfo, this.props.fields);
		return {
			config: {
				activeFields,
				resModel,
				fields,
			},
		};
	}
}
CylloActivityController.components = {
	...ActivityController.components,
	Layout
}
CylloActivityController.template = "studio.CylloActivityController"