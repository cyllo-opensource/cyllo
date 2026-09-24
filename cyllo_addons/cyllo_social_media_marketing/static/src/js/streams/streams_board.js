/** @odoo-module **/
import { registry } from "@web/core/registry";
import { Component, useRef, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { useSortable } from "@web/core/utils/sortable_owl";
import { BoardSidebar } from "./board_sidebar";
import { StreamColumn } from "./stream_column";
import { AddStreamPanel } from "./add_stream_panel";
import { reorderByDrop } from "./stream_registry";

const actionRegistry = registry.category("actions");

export class StreamsBoard extends Component {
    static template = "cyllo_social_media_marketing.StreamsBoard";
    static components = { BoardSidebar, StreamColumn, AddStreamPanel };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({
            boards: [],
            activeBoardId: false,
            showAddStream: false,
            editingColumn: false,
            loadingBoards: true,
        });

        this.columnsRef = useRef("columns");
        useSortable({
            ref: this.columnsRef,
            elements: ".o_stream_column",
            handle: ".o_stream_column_header",
            ignore: "button",
            cursor: "move",
            onDrop: ({ element, previous, next }) => {
                if (!this.activeBoard) {
                    return;
                }
                const orderedIds = reorderByDrop(
                    this.activeBoard.columns,
                    Number(element.dataset.id),
                    previous,
                    next
                );
                this.reorderColumns(orderedIds);
            },
        });

        this.loadBoards();
    }

    get activeBoard() {
        return this.state.boards.find((board) => board.id === this.state.activeBoardId) || null;
    }

    async loadBoards() {
        try {
            const boards = await this.orm.call("social.stream.board", "get_boards_with_columns", []);
            this.state.boards = boards;
            if (!this.state.activeBoardId && boards.length) {
                this.state.activeBoardId = boards[0].id;
            }
        } finally {
            this.state.loadingBoards = false;
        }
    }

    setActiveBoard(boardId) {
        this.state.activeBoardId = boardId;
    }

    async createBoard(name) {
        const board = await this.orm.call("social.stream.board", "action_create_board", [name]);
        this.state.boards.push(board);
        this.state.activeBoardId = board.id;
    }

    async renameBoard(boardId, name) {
        await this.orm.write("social.stream.board", [boardId], { name });
        const board = this.state.boards.find((b) => b.id === boardId);
        if (board) {
            board.name = name;
        }
    }

    async reorderBoards(orderedIds) {
        const boardsById = new Map(this.state.boards.map((board) => [board.id, board]));
        this.state.boards = orderedIds.map((id) => boardsById.get(id)).filter(Boolean);
        await this.orm.call("social.stream.board", "action_reorder_boards", [orderedIds]);
    }

    async reorderColumns(orderedIds) {
        const board = this.activeBoard;
        if (!board) {
            return;
        }
        const columnsById = new Map(board.columns.map((column) => [column.id, column]));
        board.columns = orderedIds.map((id) => columnsById.get(id)).filter(Boolean);
        await this.orm.call("social.stream.column", "action_reorder_columns", [orderedIds]);
    }

    async deleteBoard(boardId) {
        await this.orm.unlink("social.stream.board", [boardId]);
        this.state.boards = this.state.boards.filter((board) => board.id !== boardId);
        if (this.state.activeBoardId === boardId) {
            this.state.activeBoardId = this.state.boards.length ? this.state.boards[0].id : false;
        }
    }

    async openAddStream() {
        if (!this.activeBoard) {
            this.notification.add("Create a board first.", { type: "warning" });
            return;
        }
        this.state.editingColumn = false;
        this.state.showAddStream = true;
        await new Promise((resolve) => requestAnimationFrame(resolve));
        if (this.columnsRef.el) {
            this.columnsRef.el.scrollTo({ left: this.columnsRef.el.scrollWidth, behavior: "smooth" });
        }
    }

    openEditStream(column) {
        this.state.editingColumn = column;
        this.state.showAddStream = true;
    }

    closeAddStream() {
        this.state.showAddStream = false;
        this.state.editingColumn = false;
    }

    async onStreamAdded(result) {
        const board = this.activeBoard;
        const wasEdit = !!(board && board.columns.some((c) => c.id === result.id));
        if (board) {
            const index = board.columns.findIndex((c) => c.id === result.id);
            if (index >= 0) {
                board.columns[index] = result;
            } else {
                board.columns.push(result);
            }
        }
        this.state.showAddStream = false;
        this.state.editingColumn = false;
        if (wasEdit) {
            return;
        }
        await new Promise((resolve) => requestAnimationFrame(resolve));
        if (this.columnsRef.el) {
            this.columnsRef.el.scrollTo({ left: this.columnsRef.el.scrollWidth, behavior: "smooth" });
        }
    }

    async deleteColumn(columnId) {
        await this.orm.unlink("social.stream.column", [columnId]);
        const board = this.activeBoard;
        if (board) {
            board.columns = board.columns.filter((column) => column.id !== columnId);
        }
    }
}

actionRegistry.add("social_media_feed_dashboard_tag", StreamsBoard);
