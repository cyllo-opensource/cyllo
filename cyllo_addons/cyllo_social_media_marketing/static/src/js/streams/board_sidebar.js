/** @odoo-module **/
import { Component, useRef } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { useSortable } from "@web/core/utils/sortable_owl";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { BoardFormDialog } from "./board_form_dialog";
import { reorderByDrop } from "./stream_registry";

export class BoardSidebar extends Component {
    static template = "cyllo_social_media_marketing.BoardSidebar";
    static components = { Dropdown, DropdownItem };
    static props = {
        boards: Array,
        activeBoardId: { type: [Number, Boolean], optional: true },
        loading: { type: Boolean, optional: true },
        onSelect: Function,
        onCreate: Function,
        onRename: Function,
        onDelete: Function,
        onReorder: Function,
    };

    setup() {
        this.dialog = useService("dialog");
        this.rootRef = useRef("root");
        useSortable({
            ref: this.rootRef,
            elements: ".o_streams_board_draggable",
            handle: ".o_search_panel_label_title",
            ignore: "button",
            cursor: "move",
            onDrop: ({ element, previous, next }) => {
                const orderedIds = reorderByDrop(
                    this.props.boards,
                    Number(element.dataset.id),
                    previous,
                    next
                );
                this.props.onReorder(orderedIds);
            },
        });
    }

    openNewBoardDialog() {
        this.dialog.add(BoardFormDialog, {
            title: "New Board",
            confirmLabel: "Create",
            onConfirm: (name) => this.props.onCreate(name),
        });
    }

    startRename(board) {
        this.dialog.add(BoardFormDialog, {
            title: "Rename Board",
            confirmLabel: "Save",
            initialName: board.name,
            onConfirm: (name) => this.props.onRename(board.id, name),
        });
    }

    deleteBoard(board) {
        this.dialog.add(ConfirmationDialog, {
            title: "Delete board",
            body: `Delete board "${board.name}"? This removes all its columns.`,
            confirm: () => this.props.onDelete(board.id),
            cancel: () => {},
        });
    }
}
