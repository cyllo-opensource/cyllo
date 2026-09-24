/** @odoo-module */

import { registry } from "@web/core/registry";
const { Component, useState, onMounted, onWillUnmount } = owl;
import { useService } from "@web/core/utils/hooks";


class kitchen_screen_dashboard extends Component {

    setup() {
        this._kitchenHiddenEls = [];
        this._advancingOrderIds = new Set();
        this._dragOrderId = null;
        this._isDragging = false;
        this._onPosOrderCreationBound = this.onPosOrderCreation.bind(this);
        onMounted(() => {
            // Setup a timer to refresh the time-ago badges every minute
            this._timer = setInterval(() => {
                if (this.state) {
                    this.state.timeTick++;
                }
            }, 60000);

            // Make the kitchen screen distraction-free (no backend navbar/sidebar).
            document.body.classList.add("cyllo_kitchen_screen");
            document.documentElement.classList.add("cyllo_kitchen_screen");

            // Fallback: force-hide via inline styles to override Bootstrap `d-flex !important`.
            const selectorsToHide = [
                ".cy-left-sidebar-nav",
                ".cy-left-sidebar",
                ".cy-submenu-box",
                ".cy-right-sidebar",
                "#sidebar_panel",
                ".o_main_navbar",
                ".o_control_panel",
            ];
            selectorsToHide.forEach((selector) => {
                document.querySelectorAll(selector).forEach((el) => {
                    this._kitchenHiddenEls.push([el, el.style.display]);
                    el.style.display = "none";
                });
            });

            // Touch drag-and-drop support for tablet/mobile devices
            this._setupTouchDrag();
        });
        onWillUnmount(() => {
            document.body.classList.remove("cyllo_kitchen_screen");
            document.documentElement.classList.remove("cyllo_kitchen_screen");
            this._kitchenHiddenEls.forEach(([el, prevDisplay]) => {
                el.style.display = prevDisplay || "";
            });
            this._kitchenHiddenEls = [];
            if (this._timer) {
                clearInterval(this._timer);
            }
            this._teardownTouchDrag();
            try {
                this.busService?.removeEventListener?.("notification", this._onPosOrderCreationBound);
            } catch {
                // ignore
            }
        });

        this.busService = this.env.services.bus_service;
        this.busService.addChannel("pos_order_created");
        this.busService.addEventListener("notification", this._onPosOrderCreationBound);

        this.action = useService("action");
        this.rpc = this.env.services.rpc;
        this.action = useService("action");
        this.orm = useService("orm");
        var self = this
        this.state = useState({
            order_details: [],
            shop_id: [],
            shop_name: '',
            stages: [],
            active_stage_id: null,
            active_stage_is_done: false,
            active_stage_is_cancelled: false,
            active_stage_name: '',
            counts: {},
            lines: [],
            is_kitchen_cook: false,
            timeTick: 0,
        });
        var session_shop_id;
        if (this.props.action.context.default_shop_id) {
            sessionStorage.setItem('shop_id', this.props.action.context.default_shop_id);
            this.shop_id = this.props.action.context.default_shop_id;
            session_shop_id = sessionStorage.getItem('shop_id');
        } else {
            session_shop_id = sessionStorage.getItem('shop_id');
            this.shop_id = parseInt(session_shop_id, 10);;
        }
        self.orm.call("pos.order", "get_details", ["", self.shop_id, ""]).then(function (result) {
            self.state.order_details = result['orders']
            self.state.lines = result['order_lines']
            self.state.stages = result['stages'].map(stage => {
                // Clean up invalid or empty data
                if (!stage.image || stage.image === 'false' || stage.image.length < 50) {
                    stage.image = null;
                }
                return stage;
            });
            self.state.shop_id = self.shop_id
            self.state.shop_name = result['shop_name'] || '';
            self.state.is_kitchen_cook = !!result['is_kitchen_cook'];
            if (self.state.stages.length > 0) {
                // Prefer 'All' stage by default
                let all_stage = self.state.stages.find(s => s.name == 'All' && !s.is_done && !s.is_cancelled);
                let default_stage = all_stage || self.state.stages[0];

                self.state.active_stage_id = default_stage.id;
                self.state.active_stage_is_done = default_stage.is_done;
                self.state.active_stage_is_cancelled = default_stage.is_cancelled;
                self.state.active_stage_name = default_stage.name;
            }
            self.compute_counts();
        });
    }

    async close_kitchen_screen(e) {
        e?.stopPropagation?.();
        // NOTE: Do NOT call e.preventDefault() here — it would block the button click itself.

        // 1. Try action.restore() — works when opened as a client_action overlay/fullscreen.
        if (this.action?.restore) {
            try {
                await this.action.restore();
                return;
            } catch {
                // ignore and fallback
            }
        }

        // 2. Navigate to the kitchen screen list view directly (works for current-target actions).
        if (this.action?.doAction) {
            try {
                await this.action.doAction(
                    "cyllo_pos_kitchen_screen.action_view_pos_kitchen_screen",
                    { clearBreadcrumbs: true }
                );
                return;
            } catch {
                // ignore and fallback
            }
        }
        if (window.history.length > 1) {
            window.history.back();
        } else {
            window.location.assign("/web");
        }
    }

    on_order_drag_start(e) {
        if (!this.state.is_kitchen_cook) {
            e.preventDefault();
            return;
        }
        const orderId = Number(e.currentTarget?.dataset?.orderId);
        if (!orderId) {
            return;
        }
        this._dragOrderId = orderId;
        this._isDragging = true;
        try {
            e.dataTransfer.effectAllowed = "move";
            e.dataTransfer.setData("text/plain", String(orderId));
        } catch {
            // Ignore environments where dataTransfer is restricted.
        }
    }

    on_order_drag_end() {
        this._dragOrderId = null;
        this._isDragging = false;
        document.querySelectorAll(".kitchen_drag_over").forEach((el) => el.classList.remove("kitchen_drag_over"));
    }

    _setupTouchDrag() {
        // Self-contained touch drag support for tablets/mobiles.
        // Mirrors the dragstart / dragover / drop sequence using touch events.
        let touchDragOrderId = null;
        let ghost = null;
        let lastOverColumn = null;

        const getCardEl = (target) => target?.closest?.(".kitchen_card");
        const getColumnEl = (x, y) => {
            const el = document.elementFromPoint(x, y);
            return el?.closest?.(".kitchen_column");
        };
        const removeGhost = () => {
            if (ghost) {
                ghost.remove();
                ghost = null;
            }
        };
        const clearHighlight = () => {
            document.querySelectorAll(".kitchen_drag_over").forEach((el) => el.classList.remove("kitchen_drag_over"));
            lastOverColumn = null;
        };

        const onTouchStart = (e) => {
            if (!this.state.is_kitchen_cook) return;
            const card = getCardEl(e.target);
            if (!card) return;
            const orderId = Number(card.dataset?.orderId);
            if (!orderId) return;

            touchDragOrderId = orderId;
            this._dragOrderId = orderId;
            this._isDragging = true;

            // Create a visual ghost clone
            const rect = card.getBoundingClientRect();
            ghost = card.cloneNode(true);
            ghost.style.cssText = `
                position: fixed;
                left: ${rect.left}px;
                top: ${rect.top}px;
                width: ${rect.width}px;
                opacity: 0.75;
                pointer-events: none;
                z-index: 9999;
                border-radius: 8px;
                box-shadow: 0 8px 24px rgba(0,0,0,0.2);
                transform: scale(1.02);
                transition: none;
            `;
            document.body.appendChild(ghost);
        };

        const onTouchMove = (e) => {
            if (!touchDragOrderId || !ghost) return;
            e.preventDefault();

            const touch = e.touches[0];
            const rect = ghost.getBoundingClientRect();
            ghost.style.left = `${touch.clientX - rect.width / 2}px`;
            ghost.style.top = `${touch.clientY - rect.height / 2}px`;

            // Highlight the column below the finger
            ghost.style.display = "none";
            const col = getColumnEl(touch.clientX, touch.clientY);
            ghost.style.display = "";

            if (col !== lastOverColumn) {
                clearHighlight();
                if (col) {
                    col.classList.add("kitchen_drag_over");
                    lastOverColumn = col;
                }
            }
        };

        const onTouchEnd = async (e) => {
            if (!touchDragOrderId) return;

            const touch = e.changedTouches[0];

            // Find the column under the finger
            ghost && (ghost.style.display = "none");
            const col = getColumnEl(touch.clientX, touch.clientY);
            ghost && (ghost.style.display = "");

            removeGhost();
            clearHighlight();

            if (col) {
                const stageId = Number(col.dataset?.stageId);
                if (stageId) {
                    await this.move_order_to_stage(touchDragOrderId, stageId);
                }
            }

            touchDragOrderId = null;
            this._dragOrderId = null;
            this._isDragging = false;
        };

        // Store references so we can remove them on unmount
        this._touchDragStart = onTouchStart;
        this._touchDragMove = onTouchMove;
        this._touchDragEnd = onTouchEnd;

        document.addEventListener("touchstart", onTouchStart, { passive: true });
        document.addEventListener("touchmove", onTouchMove, { passive: false });
        document.addEventListener("touchend", onTouchEnd, { passive: true });
    }

    _teardownTouchDrag() {
        if (this._touchDragStart) document.removeEventListener("touchstart", this._touchDragStart);
        if (this._touchDragMove) document.removeEventListener("touchmove", this._touchDragMove);
        if (this._touchDragEnd) document.removeEventListener("touchend", this._touchDragEnd);
        this._touchDragStart = null;
        this._touchDragMove = null;
        this._touchDragEnd = null;
    }

    on_stage_drag_over(e) {
        e.preventDefault();
        e.currentTarget?.classList?.add("kitchen_drag_over");
    }

    on_stage_drag_leave(e) {
        e.currentTarget?.classList?.remove("kitchen_drag_over");
    }

    async on_stage_drop(e) {
        e.preventDefault();
        e.stopPropagation();
        e.currentTarget?.classList?.remove("kitchen_drag_over");
        if (!this.state.is_kitchen_cook) {
            return;
        }

        const stageId = Number(e.currentTarget?.dataset?.stageId);
        if (!stageId) {
            return;
        }
        let orderId = this._dragOrderId;
        try {
            const dt = e.dataTransfer?.getData("text/plain");
            if (dt) {
                orderId = Number(dt);
            }
        } catch {
            // ignore
        }
        if (!orderId) {
            return;
        }
        await this.move_order_to_stage(orderId, stageId);
        this._dragOrderId = null;
        this._isDragging = false;
    }

    async move_order_to_stage(orderId, stageId) {
        if (!this.state.is_kitchen_cook) {
            return;
        }
        const order = (this.state.order_details || []).find((o) => o.id === orderId);
        const stage = (this.state.stages || []).find((s) => s.id === stageId);
        if (!order || !stage) {
            return;
        }
        const currentStageId = order.kitchen_stage_id?.[0];
        if (currentStageId === stageId) {
            return;
        }
        const resById = await this.orm.call("pos.order", "set_kitchen_stage", [[orderId], stageId]);
        const res = resById ? resById[orderId] : null;
        if (res) {
            order.order_status = res.order_status;
            order.kitchen_stage_id = res.kitchen_stage_id;
        } else {
            // Fallback: optimistic update for immediate UI feedback.
            order.kitchen_stage_id = [stageId, stage.name];
            // Keep legacy status in an "active" value unless this is a done/cancelled stage.
            order.order_status = stage.is_done ? "ready" : (stage.is_cancelled ? "cancel" : "waiting");
        }
        this.compute_counts();
    }

    _getActiveStages() {
        return (this.state.stages || [])
            .filter((s) => !s.is_done && !s.is_cancelled && s.name !== "All")
            .slice()
            .sort((a, b) => (a.sequence || 0) - (b.sequence || 0) || (a.id || 0) - (b.id || 0));
    }

    _getDoneStage() {
        return (this.state.stages || []).find((s) => !!s.is_done) || null;
    }

    _getCancelledStage() {
        return (this.state.stages || []).find((s) => !!s.is_cancelled) || null;
    }

    _inferStageIdFromLegacyStatus(order) {
        const doneStage = this._getDoneStage();
        const cancelledStage = this._getCancelledStage();
        const activeStages = this._getActiveStages();
        if (order.order_status === "ready") return doneStage?.id || null;
        if (order.order_status === "cancel") return cancelledStage?.id || null;
        return activeStages[0]?.id || null;
    }

    _getOrderStageId(order) {
        return order?.kitchen_stage_id?.[0] || this._inferStageIdFromLegacyStatus(order);
    }

    _orderMatchesStage(order, stage) {
        if (!order || !stage) {
            return false;
        }
        if (this.state.shop_id !== order.config_id?.[0]) {
            return false;
        }

        if (this._isAllStage(stage)) {
            return ["draft", "waiting", "ready", "cancel"].includes(order.order_status);
        }
        return this._getOrderStageId(order) === stage.id;
    }

    shouldShowOrder(order) {
        const stage = (this.state.stages || []).find((s) => s.id === this.state.active_stage_id);
        return this._orderMatchesStage(order, stage);
    }

    _isAllStage(stage) {
        return !!stage && stage.name === "All" && !stage.is_done && !stage.is_cancelled;
    }

    _getBoardStages() {
        const stages = (this.state.stages || []);
        // Always show all non-"All" stages on the board at the same time.
        const activeStages = stages
            .filter((s) => !this._isAllStage(s) && !s.is_done && !s.is_cancelled)
            .slice()
            .sort((a, b) => (a.sequence || 0) - (b.sequence || 0) || (a.id || 0) - (b.id || 0));
        const doneStages = stages
            .filter((s) => !this._isAllStage(s) && !!s.is_done)
            .slice()
            .sort((a, b) => (a.sequence || 0) - (b.sequence || 0) || (a.id || 0) - (b.id || 0));
        const cancelledStages = stages
            .filter((s) => !this._isAllStage(s) && !!s.is_cancelled)
            .slice()
            .sort((a, b) => (a.sequence || 0) - (b.sequence || 0) || (a.id || 0) - (b.id || 0));

        return [...activeStages, ...doneStages, ...cancelledStages];
    }

    getStageColumns() {
        const orders = (this.state.order_details || []);
        return this._getBoardStages().map((stage) => {
            const stageOrders = orders.filter((order) => this._orderMatchesStage(order, stage));
            return {
                stage,
                orders: stageOrders,
                count: stageOrders.length,
                // Used by the template to decide whether the "remove" (x) button should appear.
                isReadyStage: !!stage.is_done,
                isCancelStage: !!stage.is_cancelled,
            };
        });
    }

    compute_counts() {
        let counts = {};
        (this.state.stages || []).forEach((stage) => {
            counts[stage.id] = (this.state.order_details || []).filter((order) =>
                this._orderMatchesStage(order, stage)
            ).length;
        });
        this.state.counts = counts;
    }

    //Calling the onPosOrderCreation when an order is created or edited on the backend and return the notification
    onPosOrderCreation(message) {
        if (owl.status(this) === "destroyed") {
            return;
        }
        let payload = message.detail[0].payload
        var self = this
        if (payload.message == "pos_order_created" && payload.res_model == "pos.order") {
            self.orm.call("pos.order", "get_details", ["", self.shop_id, ""]).then(function (result) {
                if (owl.status(self) === "destroyed") {
                    return;
                }
                self.state.order_details = result['orders']
                self.state.lines = result['order_lines']
                self.state.stages = result['stages'].map(stage => {
                    if (!stage.image || stage.image === 'false' || stage.image.length < 50) {
                        stage.image = null;
                    }
                    return stage;
                });
                self.state.shop_id = self.shop_id
                self.state.is_kitchen_cook = !!result['is_kitchen_cook'];
                if (self.state.active_stage_id) {
                    self.select_stage(self.state.active_stage_id);
                }
                self.compute_counts();
            }).catch(function () {
                // Ignore if the component is already gone.
            });
        }
    }

    get_time_ago(date_order) {
        if (!date_order) return "";
        try {
            // date_order from pos.read() is typically a string "YYYY-MM-DD HH:MM:SS" (UTC)
            let order_time;
            if (typeof date_order === 'string') {
                // Try converting the UTC string to local time (naive approach)
                order_time = new Date(date_order + "Z").getTime();
            } else {
                order_time = new Date(date_order).getTime();
            }
            let diff_ms = new Date().getTime() - order_time;
            let diff_mins = Math.floor(diff_ms / 60000);
            if (diff_mins < 0) diff_mins = 0; // Prevent negative mins if clocks slightly out of sync

            if (diff_mins === 0) return "Just now";
            if (diff_mins < 60) return diff_mins + " min ago";

            let diff_hours = Math.floor(diff_mins / 60);
            return diff_hours + " hr ago";
        } catch (e) {
            return "";
        }
    }

    // click on the order card for the next stage n
    // cancel the order from the kitchen
    cancel_order(e) {
        if (!this.state.is_kitchen_cook) { return; }
        var input_id = $("#" + e.target.id).val();
        this.orm.call("pos.order", "order_progress_cancel", [Number(input_id)])
        var current_order = this.state.order_details.filter((order) => order.id == input_id)
        if (current_order) {
            current_order[0].order_status = 'cancel'
            this.compute_counts();
        }
    }
    // accept the order from the kitchen
    accept_order(e) {
        if (!this.state.is_kitchen_cook) { return; }
        var input_id = $("#" + e.target.id).val();
        ScrollReveal().reveal("#" + e.target.id, {
            delay: 1000,
            duration: 2000,
            opacity: 0,
            distance: "50%",
            origin: "top",
            reset: true,
            interval: 600,
        });
        var self = this
        this.orm.call("pos.order", "order_progress_draft", [Number(input_id)])
        var current_order = this.state.order_details.filter((order) => order.id == input_id)
        if (current_order) {
            current_order[0].order_status = 'waiting'
            this.compute_counts();
        }
    }

    // change stage
    // change stage
    select_stage(stage_id) {
        this.state.active_stage_id = stage_id;
        let selected_stage = this.state.stages.find(s => s.id == stage_id);
        if (selected_stage) {
            this.state.active_stage_is_done = selected_stage.is_done;
            this.state.active_stage_is_cancelled = selected_stage.is_cancelled;
            this.state.active_stage_name = selected_stage.name;
        }
    }
    // change the status of the order from the kitchen
    done_order(e) {
        if (!this.state.is_kitchen_cook) { return; }
        var self = this;
        var input_id = $("#" + e.target.id).val();
        this.orm.call("pos.order", "order_progress_change", [Number(input_id)])
        var current_order = this.state.order_details.filter((order) => order.id == input_id)
        if (current_order) {
            current_order[0].order_status = 'ready'
        }
    }
    // change the status of the product from the kitchen
    accept_order_line(e) {
        if (!this.state.is_kitchen_cook) { return; }
        var input_id = $("#" + e.target.id).val();
        this.orm.call("pos.order.line", "order_progress_change", [Number(input_id)])
        var current_order_line = this.state.lines.filter((order_line) => order_line.id == input_id)
        if (current_order_line) {
            if (current_order_line[0].order_status == 'ready') {
                current_order_line[0].order_status = 'waiting'
            }
            else {
                current_order_line[0].order_status = 'ready'
            }
        }
    }

    on_line_click(e, order_status) {
        // Prevent card click (auto-advance) when interacting with a line.
        e.stopPropagation();
        e.preventDefault();
        if (!this.state.is_kitchen_cook) { return; }
        if (order_status !== 'waiting') {
            return;
        }
        const input_id = Number(e.currentTarget.value);
        if (!input_id) {
            return;
        }
        this.orm.call("pos.order.line", "order_progress_change", [input_id])
        const current_order_line = this.state.lines.find((order_line) => order_line.id === input_id);
        if (current_order_line) {
            current_order_line.order_status = current_order_line.order_status === 'ready' ? 'waiting' : 'ready';
        }
    }

    async advance_order(e) {
        if (!this.state.is_kitchen_cook) {
            return;
        }
        if (this._isDragging) {
            return;
        }
        // Ignore clicks from interactive children (e.g. order lines).
        if (e.target && e.target.closest && e.target.closest(".list-group-item")) {
            return;
        }
        const order_id = Number(e.currentTarget?.dataset?.orderId);
        if (!order_id) {
            return;
        }
        const order = this.state.order_details.find((o) => o.id === order_id);
        if (!order) {
            return;
        }
        if (this._advancingOrderIds.has(order_id)) {
            return;
        }
        // No auto-advance for cancelled or completed orders.
        if (order.order_status === 'cancel' || order.order_status === 'ready') {
            return;
        }

        this._advancingOrderIds.add(order_id);
        try {
            const stages = (this.state.stages || [])
                .filter((s) => !this._isAllStage(s) && !s.is_cancelled)
                .slice()
                .sort((a, b) => (a.sequence || 0) - (b.sequence || 0) || (a.id || 0) - (b.id || 0));
            const currentStageId = this._getOrderStageId(order);
            const idx = stages.findIndex((s) => s.id === currentStageId);
            if (idx < 0) {
                const first = stages[0];
                if (first) {
                    await this.move_order_to_stage(order_id, first.id);
                }
                return;
            }
            const next = stages[idx + 1];
            if (!next) {
                return;
            }
            await this.move_order_to_stage(order_id, next.id);
        } finally {
            this._advancingOrderIds.delete(order_id);
        }
    }

    async remove_completed_order(e) {
        e.stopPropagation();
        e.preventDefault();
        if (!this.state.is_kitchen_cook) { return; }
        const order_id = Number(e.currentTarget?.dataset?.orderId);
        if (!order_id) {
            return;
        }
        await this.orm.call("pos.order", "remove_from_kitchen", [order_id]);
        this.state.order_details = (this.state.order_details || []).filter((o) => o.id !== order_id);
        this.compute_counts();
    }
    // remove the order from the kitchen
    remove_order(e) {
        if (!this.state.is_kitchen_cook) { return; }
        var input_id = $("#" + e.target.id).val();
        this.orm.call("pos.order", "remove_from_kitchen", [Number(input_id)])
        this.state.order_details = this.state.order_details.filter((order) => order.id != input_id);
        this.compute_counts();
    }

}
kitchen_screen_dashboard.template = 'KitchenCustomDashBoard';
registry.category("actions").add("kitchen_custom_dashboard_tags", kitchen_screen_dashboard);
