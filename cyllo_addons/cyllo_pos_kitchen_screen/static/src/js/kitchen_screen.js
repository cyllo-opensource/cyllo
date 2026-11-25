/** @odoo-module */

import { registry } from "@web/core/registry";
const { Component, useState, onMounted, onWillUnmount } = owl;
import { useService } from "@web/core/utils/hooks";

const KS_EDGE_ZONE_PX = 70;
const KS_EDGE_MARGIN_PX = 24;
const KS_SCROLL_MIN_PX_MS = 0.35;
const KS_SCROLL_MAX_PX_MS = 1.10;
const KS_DRAG_THRESHOLD_PX = 10;
const KS_GHOST_MARGIN_PX = 8;

class kitchen_screen_dashboard extends Component {

    setup() {
        this._kitchenHiddenEls = [];
        this._advancingOrderIds = new Set();
        this._dragOrderId = null;
        this._isDragging = false;
        this._onPosOrderCreationBound = this.onPosOrderCreation.bind(this);
        this._ks_board_el = null;
        this._ks_scroll_raf = null;
        this._ks_scroll_dir = 0;
        this._ks_edge_depth = 0;
        this._ks_last_time = null;
        this._ks_last_x = 0;
        this._ks_last_y = 0;
        this._ks_last_col = null;
        this._ks_prev_snap = "";
        this._ks_prev_behavior = "";
        this._ks_remove_ghost = null;
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
       /**
     * Single source of truth for the "kitchen_drag_over" drop highlight.
     * Used both by onTouchMove and by the auto-scroll RAF loop so that the
     * highlighted column always matches what is actually under the finger,
     * even while the board slides underneath a stationary finger.
     */
    _ks_set_highlight(col) {
        if (col === this._ks_last_col) return;
        document.querySelectorAll(".kitchen_drag_over")
            .forEach((el) => el.classList.remove("kitchen_drag_over"));
        if (col) {
            col.classList.add("kitchen_drag_over");
        }
        this._ks_last_col = col;
    }

    /**
     * Remember which board element is being auto-scrolled for this drag and
     * neutralize scroll-snap / smooth-behavior while dragging (they fight the
     * manual scrollLeft updates). Prior inline values are restored on release.
     */
    _ks_set_board(board) {
        if (this._ks_board_el === board) return;
        this._ks_release_board();
        this._ks_board_el = board || null;
        if (this._ks_board_el) {
            this._ks_prev_snap = this._ks_board_el.style.scrollSnapType;
            this._ks_prev_behavior = this._ks_board_el.style.scrollBehavior;
            this._ks_board_el.style.scrollSnapType = "none";
            this._ks_board_el.style.scrollBehavior = "auto";
        }
    }

    /**
     * Stop auto-scroll and restore the board's original scroll-snap /
     * scroll-behavior. Called on touchend / touchcancel / unmount.
     */
    _ks_release_board() {
        this._ks_stop_autoscroll();
        if (this._ks_board_el) {
            this._ks_board_el.style.scrollSnapType = this._ks_prev_snap || "";
            this._ks_board_el.style.scrollBehavior = this._ks_prev_behavior || "";
            this._ks_board_el = null;
        }
    }

    /** Stop the RAF loop and reset the scroll direction / edge depth. */
    _ks_stop_autoscroll() {
        if (this._ks_scroll_raf) {
            cancelAnimationFrame(this._ks_scroll_raf);
            this._ks_scroll_raf = null;
        }
        this._ks_scroll_dir = 0;
        this._ks_edge_depth = 0;
        this._ks_last_time = null;
    }

    /**
     * Start (or keep) the requestAnimationFrame loop that slowly moves the
     * board in the direction held by the finger. Speed ramps with
     * _ks_edge_depth (0..1) so the default drift stays "slow".
     */
    _ks_start_autoscroll() {
        if (this._ks_scroll_raf) return;
        this._ks_last_time = performance.now();
        const step = (now) => {
            const dt = this._ks_last_time ? Math.max(0, now - this._ks_last_time) : 16.7;
            this._ks_last_time = now;
            if (this._ks_board_el && this._ks_scroll_dir) {
                const speed = KS_SCROLL_MIN_PX_MS +
                    (KS_SCROLL_MAX_PX_MS - KS_SCROLL_MIN_PX_MS) * this._ks_edge_depth;
                this._ks_board_el.scrollLeft += this._ks_scroll_dir * speed * dt;
                // Re-highlight the drop column while the board slides under the finger
                const el = document.elementFromPoint(this._ks_last_x, this._ks_last_y);
                const col = el?.closest?.(".kitchen_column");
                if (col !== this._ks_last_col) {
                    this._ks_set_highlight(col);
                }
            }
            this._ks_scroll_raf = requestAnimationFrame(step);
        };
        this._ks_scroll_raf = requestAnimationFrame(step);
    }

    /**
     * Edge detection: called with the finger's client X on every touchmove.
     * Holding the finger near the RIGHT edge reveals the stages on the right
     * (board scrolls left), near the LEFT edge reveals the stages on the left.
     */
    _ks_update_edge_scroll(client_x) {
        const board = this._ks_board_el;
        if (!board) return;
        const rect = board.getBoundingClientRect();
        if (client_x > rect.right - KS_EDGE_ZONE_PX) {
            this._ks_edge_depth = Math.min(1,
                (client_x - (rect.right - KS_EDGE_ZONE_PX)) /
                Math.max(1, KS_EDGE_ZONE_PX - KS_EDGE_MARGIN_PX));
            this._ks_scroll_dir = 1;
            this._ks_start_autoscroll();
        } else if (client_x < rect.left + KS_EDGE_ZONE_PX) {
            this._ks_edge_depth = Math.min(1,
                ((rect.left + KS_EDGE_ZONE_PX) - client_x) /
                Math.max(1, KS_EDGE_ZONE_PX - KS_EDGE_MARGIN_PX));
            this._ks_scroll_dir = -1;
            this._ks_start_autoscroll();
        } else if (this._ks_scroll_dir) {
            this._ks_stop_autoscroll();
        }
    }


    _setupTouchDrag() {

        let touchDragOrderId = null;
        let ghost = null;
        let ghostWrap = null;
        let dragArmed = false;
        let touchStartX = 0;
        let touchStartY = 0;
        let dragSourceCard = null;

        const getCardEl = (target) => target?.closest?.(".kitchen_card");
        const getColumnEl = (x, y) => {
            const el = document.elementFromPoint(x, y);
            return el?.closest?.(".kitchen_column");
        };
        const removeGhost = () => {

            if (ghostWrap) {
                ghostWrap.remove();
                ghostWrap = null;
            }
            if (ghost) {
                ghost.remove();
                ghost = null;
            }
        };

        const onTouchStart = (e) => {
            if (!this.state.is_kitchen_cook) return;
            const card = getCardEl(e.target);
            if (!card) return;
            const orderId = Number(card.dataset?.orderId);
            if (!orderId) return;

            const touch = e.touches[0];
            touchDragOrderId = orderId;
            this._dragOrderId = orderId;
            // No ghost here and _isDragging stays false. The drag (and its
            // overlay) only arms after real finger travel — a tap must remain
            // a tap so its click reaches advance_order().
            dragArmed = false;
            touchStartX = touch.clientX;
            touchStartY = touch.clientY;
            dragSourceCard = card;

            // Keep: prepare edge auto-scroll for the potential drag.
            // (Board is released again instantly in the tap branch of onTouchEnd.)
            this._ks_last_x = 0;
            this._ks_last_y = 0;
            this._ks_set_highlight(null);
            this._ks_set_board(card.closest(".kitchen_board"));
        };


        const createGhost = () => {
            const card = dragSourceCard;
            const rect = card.getBoundingClientRect();
            ghostWrap = document.createElement("div");
            ghostWrap.className =
                "kitchen body_wrapper screen_info wrapper kitchen_column kitchen_column_body";
            ghostWrap.style.cssText = "display: contents;";
            ghost = card.cloneNode(true);
            ghost.style.cssText = `
                position: fixed;
                left: ${rect.left}px;
                top: ${rect.top}px;
                width: ${rect.width}px;
                height: ${rect.height}px;
                overflow: hidden;
                opacity: 0.75;
                pointer-events: none;
                z-index: 9999;
                border-radius: 8px;
                box-shadow: 0 8px 24px rgba(0,0,0,0.2);
                transform: none;
                margin: 0 !important;
                transition: none;
            `;
            ghostWrap.appendChild(ghost);
            document.body.appendChild(ghostWrap);
        };

        const onTouchMove = (e) => {
            if (!touchDragOrderId) return;
            e.preventDefault();

            const touch = e.touches[0];

            // Arm the drag only after real finger travel. Before that, nothing
            // visual happens on the card.
            if (!dragArmed) {
                const dx = touch.clientX - touchStartX;
                const dy = touch.clientY - touchStartY;
                if ((dx * dx + dy * dy) < (KS_DRAG_THRESHOLD_PX * KS_DRAG_THRESHOLD_PX)) {
                    return;
                }
                dragArmed = true;
                this._isDragging = true;
                createGhost();
            }
            if (!ghost) return;

            // Keep: finger coords for the auto-scroll highlight sync.
            this._ks_last_x = touch.clientX;
            this._ks_last_y = touch.clientY;

            const rect = ghost.getBoundingClientRect();

            // Clamp the ghost inside the viewport — it can never overflow the
            // mobile screen. Column detection below still uses the RAW finger
            // coordinates, so drag machinery is unaffected.
            const maxX = Math.max(KS_GHOST_MARGIN_PX,
                window.innerWidth - rect.width - KS_GHOST_MARGIN_PX);
            const maxY = Math.max(KS_GHOST_MARGIN_PX,
                window.innerHeight - rect.height - KS_GHOST_MARGIN_PX);
            ghost.style.left = `${Math.min(Math.max(touch.clientX - rect.width / 2,
                KS_GHOST_MARGIN_PX), maxX)}px`;
            ghost.style.top = `${Math.min(Math.max(touch.clientY - rect.height / 2,
                KS_GHOST_MARGIN_PX), maxY)}px`;

            // Highlight the column below the finger
            ghost.style.display = "none";
            const col = getColumnEl(touch.clientX, touch.clientY);
            ghost.style.display = "";

            // Shared highlight helper (kept in sync with the auto-scroll loop)
            this._ks_set_highlight(col);

            // Start/stop edge auto-scroll depending on finger position
            this._ks_update_edge_scroll(touch.clientX);
        };

        const onTouchEnd = async (e) => {
            if (!touchDragOrderId) return;

            // It was a tap, never a drag. Reset state immediately so the
            // browser's click reaches advance_order() (fixes the _isDragging
            // race that could swallow taps), and restore the board since no
            // drop will happen.
            if (!dragArmed) {
                this._ks_release_board();
                this._ks_set_highlight(null);
                touchDragOrderId = null;
                this._dragOrderId = null;
                this._isDragging = false;
                return;
            }

            const touch = e.changedTouches[0];

            // Find the column under the finger
            ghost && (ghost.style.display = "none");
            const col = getColumnEl(touch.clientX, touch.clientY);
            ghost && (ghost.style.display = "");

            removeGhost();

            // Stop auto-scroll, restore the board, clear highlight
            // (done BEFORE the async stage move so scrolling halts instantly)
            this._ks_release_board();
            this._ks_set_highlight(null);

            if (col) {
                const stageId = Number(col.dataset?.stageId);
                if (stageId) {
                    await this.move_order_to_stage(touchDragOrderId, stageId);
                }
            }

            dragArmed = false;
            dragSourceCard = null;
            touchDragOrderId = null;
            this._dragOrderId = null;
            this._isDragging = false;
        };

        // Browsers cancel touches for system gestures; without this the ghost
        // would stay on screen and the auto-scroll loop would keep running
        const onTouchCancel = () => {
            removeGhost();
            this._ks_release_board();
            this._ks_set_highlight(null);
            dragArmed = false;
            dragSourceCard = null;
            touchDragOrderId = null;
            this._dragOrderId = null;
            this._isDragging = false;
        };

        // Store references so we can remove them on unmount
        this._touchDragStart = onTouchStart;
        this._touchDragMove = onTouchMove;
        this._touchDragEnd = onTouchEnd;
        this._touchDragCancel = onTouchCancel;
        this._ks_remove_ghost = removeGhost;   // NEW — used by teardown cleanup

        document.addEventListener("touchstart", onTouchStart, { passive: true });
        document.addEventListener("touchmove", onTouchMove, { passive: false });
        document.addEventListener("touchend", onTouchEnd, { passive: true });
        document.addEventListener("touchcancel", onTouchCancel, { passive: true });
    }

    _teardownTouchDrag() {
        if (this._touchDragStart) document.removeEventListener("touchstart", this._touchDragStart);
        if (this._touchDragMove) document.removeEventListener("touchmove", this._touchDragMove);
        if (this._touchDragEnd) document.removeEventListener("touchend", this._touchDragEnd);
        if (this._touchDragCancel) document.removeEventListener("touchcancel", this._touchDragCancel);
        this._touchDragStart = null;
        this._touchDragMove = null;
        this._touchDragEnd = null;
        this._touchDragCancel = null;
        this._ks_remove_ghost?.();      // NEW — remove ghost + wrapper if unmounting mid-drag
        this._ks_remove_ghost = null;   // NEW
        this._ks_release_board();       // cancels the RAF loop + restores scroll-snap
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