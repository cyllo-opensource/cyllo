/** @odoo-module **/
import { AccountMoveListController } from "@account/components/bills_upload/bills_upload";
import { AccountMoveUploadKanbanController } from '@account/components/bills_upload/bills_upload';
import { CogMenuList } from "@cyllo_base/js/cog_menu_form";
import { View } from "@web/views/view";
import { ListController } from "@web/views/list/list_controller";
import { KanbanController } from "@web/views/kanban/kanban_controller";

AccountMoveListController.components={
   ...ListController.components, ...AccountMoveListController.components, CogMenuList, View
}

AccountMoveUploadKanbanController.components={
   ...KanbanController.components, ...AccountMoveUploadKanbanController.components, CogMenuList
}