/** @odoo-module **/
import {registry} from "@web/core/registry";
import {StackItem, StackKpiItem, StackTableItem} from "./stack_item";
import {CylloDashboard} from "./cyllo_dashboard";
import {browser} from "@web/core/browser/browser";
const {useState, useRef, onMounted, onWillUnmount, status} = owl;


class EditDashboard extends CylloDashboard {
    setup() {
        super.setup();
        this.edit = true;
        this.stackItems = {};
        this.ref = useRef('chart-container');
        this.state = useState({
            change: false,
            rearrange: true,
            gridStackData: [],
            editLoading: true,
        });
        onMounted(this.fetchData);
        onWillUnmount(() => {
            if (this._gridResizeObserver) this._gridResizeObserver.disconnect();
        });
        this.rearrangeId = 1;
    }

    rearrange() {
        if (!this.stack || this.state.editLoading) return;
        try {
            const newPosition = {x: 0, y: 0, w: 0, h: 0, items: {0: [0]}, type: "kpi"};
            const updates = [];
            for (const val of this.shuffleArrayItems) {
                const {height: rawH, width: chartWidth} = this.getChartSizes(val.type, this.rearrangeId);
                const origItem = this.state.sortedItems.find(i => i.id === val.id);
                const kpiMinH = val.type === 'kpi' ? (origItem?.kpi_target ? 2 : 1) : 0;
                const chartHeight = Math.max(rawH, kpiMinH);
                if (val.type !== 'kpi' && newPosition.type === 'kpi') {
                    newPosition.x = 0;
                    newPosition.y = Math.max(...newPosition.items[newPosition.y]);
                }
                if ((newPosition.x + chartWidth) > 12) {
                    newPosition.x = 0;
                    newPosition.y = Math.max(...newPosition.items[newPosition.y]);
                }
                newPosition.type = val.type;
                if (!newPosition.items[newPosition.y]) {
                    newPosition.items[newPosition.y] = [newPosition.y + chartHeight];
                } else {
                    newPosition.items[newPosition.y].push(newPosition.y + chartHeight);
                }
                updates.push({id: val.id, x: newPosition.x, y: newPosition.y, w: chartWidth, h: chartHeight});
                newPosition.x += chartWidth;
            }
            this.stack.batchUpdate();
            for (const {id, x, y, w, h} of updates) {
                const el = this.ref.el.querySelector(`#elem_${id}`);
                if (el) this.stack.update(el, {x, y, w, h});
            }
            this.stack.batchUpdate(false);
            for (const {id, w, h} of updates) {
                const stackItem = this.stackItems[`elem_${id}`];
                if (stackItem) stackItem.reRender(false, h, w);
            }
            this.state.change = true;
            this.rearrangeId++;
        } catch(e) { console.error('Rearrange error:', e); }
    }

    get shuffleArrayItems() {
        const array = [...this.vals.children];
        array.sort((a, b) => {
            const isNoResizeA = a.noResize === true;
            const isNoResizeB = b.noResize === true;
            if (isNoResizeA && !isNoResizeB) return -1;
            if (!isNoResizeA && isNoResizeB) return 1;
            return Math.random() - 0.5;
        });
        return array;
    }


    async fetchData() {
        const containerEl = this.ref.el;
        if (!containerEl) return;


        const containerWidth = containerEl.clientWidth ||
                               containerEl.offsetWidth ||
                               (window.innerWidth - 250);
        const CELL_SIZE = Math.max(Math.round(containerWidth / 12), 60);
        this.pixelSize = CELL_SIZE;
        this.gridScale = Math.max(Math.round(CELL_SIZE / 19), 1);

        const MARGIN = 4;

        // Initialize GridStack on the container element (official demo pattern)
        this.stack = GridStack.init({
            float: true,
            cellHeight: CELL_SIZE,
            column: 12,
            margin: MARGIN,
        }, containerEl);


        containerEl.style.setProperty('--gs-item-margin-top',    `${MARGIN}px`);
        containerEl.style.setProperty('--gs-item-margin-right',  `${MARGIN}px`);
        containerEl.style.setProperty('--gs-item-margin-bottom', `${MARGIN}px`);
        containerEl.style.setProperty('--gs-item-margin-left',   `${MARGIN}px`);

        // Cycle-breaker: engine.moveNode ↔ engine._fixCollisions can recurse
        // infinitely when A's collision-fix tries to move B which tries to move A.
        const _eng = this.stack.engine;
        const _origMoveNode = _eng.moveNode;
        const _movingNodes = new Set();
        _eng.moveNode = function(node, opts) {
            const id = node._id;
            if (_movingNodes.has(id)) return false;
            _movingNodes.add(id);
            try { return _origMoveNode.apply(this, [node, opts]); }
            finally { _movingNodes.delete(id); }
        };

        // Dot-grid background sizing
        const colWidth = containerWidth / 12;
        containerEl.style.setProperty('--gs-column-width', colWidth + 'px');
        containerEl.style.setProperty('--gs-cell-height', CELL_SIZE + 'px');
        containerEl.style.backgroundSize = `${colWidth}px ${CELL_SIZE}px`;
        containerEl.style.backgroundPosition = '-4px -4px';

        if (!this.state.width) this.state.width = colWidth;

        // Responsive cell sizing
        if (this._gridResizeObserver) this._gridResizeObserver.disconnect();
        this._gridResizeObserver = new ResizeObserver(() => {
            const newWidth = containerEl.clientWidth || containerEl.offsetWidth;
            if (!newWidth) return;
            const newColWidth = newWidth / 12;
            const newCellSize = Math.max(Math.round(newColWidth), 60);
            containerEl.style.setProperty('--gs-column-width', newColWidth + 'px');
            containerEl.style.setProperty('--gs-cell-height', newCellSize + 'px');
            containerEl.style.backgroundSize = `${newColWidth}px ${newCellSize}px`;
            containerEl.style.backgroundPosition = '-4px -4px';
            if (this.stack) this.stack.cellHeight(newCellSize);
            this.pixelSize = newCellSize;
            this.gridScale = Math.max(Math.round(newCellSize / 19), 1);
            this.state.width = newColWidth;
        });
        this._gridResizeObserver.observe(containerEl);

        // Fetch data for all dashboard items
        const dataPromises = this.state.sortedItems.map(item => {
            const sql = item.query.replace(/\n/g, ' ');
            return this.orm.call("dashboard.config", "sql_execute", [sql])
                .then(res => ({ item, res }))
                .catch(err => {
                    console.error("fetchData sql error:", err);
                    return { item, res: [] };
                });
        });
        const results = await Promise.all(dataPromises);


        results.forEach(({ item, res }) => {
            let measures;
            try { measures = eval(item.measure); } catch(e) { measures = []; }

            const props = {
                data: res, name: item.name, measures,
                dimension: item.dimension, dimension_axis: item.dimension_axis,
                type: item.type, id: item.id,
            };
            if (item.type === 'kpi') props.kpi = this.getKpi(item);

            const gridOptions = this.gridValues(item);

            // Outer element — becomes .grid-stack-item after makeWidget()
            const itemEl = document.createElement('div');
            itemEl.id = `elem_${item.id}`;
            itemEl.classList.add('card', 'edit_elem');
            itemEl.sheetId = item.id;
            itemEl.resId = this.id;


            const contentEl = document.createElement('div');
            contentEl.className = 'grid-stack-item-content';
            itemEl.appendChild(contentEl);

            // Register with GridStack — appends to container and applies gs-* attrs
            this.stack.makeWidget(itemEl, gridOptions);

            const unit = this.pixelSize || 20;
            if (item.type === 'kpi') {
                this.stackItems[itemEl.id] = new StackKpiItem(contentEl, props, this.env, { unit });
            } else if (item.type === 'table') {
                this.stackItems[itemEl.id] = new StackTableItem(contentEl, props, this.env, {
                    theme: this.themeState.currentTheme, unit,
                });
            } else {
                this.stackItems[itemEl.id] = new StackItem(contentEl, props, this.themeState.currentTheme, {
                    themeColor: this.themeState.theme.theme_color_ids,
                    unit, graph_height: gridOptions.h, isDarkMode: this.state.darkMode,
                });
            }
        });

        this.stack.disable();
        this.vals = this.stack.save(false, true);

        await Promise.allSettled(
            Object.values(this.stackItems).map(item => item.ready || Promise.resolve())
        );

        setTimeout(() => {
            if (status(this) === "destroyed") return;
            this.stack.float(true);
            this.stack.enable();
            this.state.editLoading = false;
            requestAnimationFrame(() => requestAnimationFrame(() => {
                if (status(this) === "destroyed") return;
                Object.values(this.stackItems).forEach(item => {
                    if (item.eChart) item.eChart.resize();
                });
                this._warmUpDrag();
            }));
        }, 350);

        this.stack.on('change', this.onChange.bind(this));
        this.stack.on('dragstart', () => {
            Object.values(this.stackItems).forEach(item => {
                if (item.resizeObserver) item.resizeObserver.disconnect();
            });
            document.body.style.cursor = 'grabbing';
        });
        this.stack.on('dragstop', (...args) => {
            document.body.style.cursor = '';
            this.dragStop(...args);
        });
        this.stack.on('resize', (event, el) => {
            const stackItem = this.stackItems[el.id];
            const h = el?.gridstackNode?.h;
            const w = el?.gridstackNode?.w;
            if (stackItem) stackItem.reRender(false, h, w);
        });
    }

    onSave() {
        const vals = this.stack.save(false, true);
        // GridStack's save() omits w/h when they equal its default (1), so a KPI
        // resized to h=1 loses its height and the backend can't tell it apart from
        // "unset". Backfill explicit x/y/w/h from the live grid nodes so every
        // item's real size is persisted.
        (vals.children || []).forEach(child => {
            const el = this.ref.el.querySelector(`#elem_${child.id}`);
            const node = el?.gridstackNode;
            if (node) {
                child.x = node.x;
                child.y = node.y;
                child.w = node.w;
                child.h = node.h;
            }
        });
        this.orm.call("dashboard.config", "save_position", [this.id, vals]);
        this.disableChange();
        this.vals = vals;
    }

    async onDiscard() {
        this.stack.batchUpdate();
        for (const val of this.vals.children) {
            const el = this.ref.el.querySelector(`#elem_${val.id}`);
            if (el) this.stack.update(el, {x: val.x, y: val.y, w: val.w, h: val.h});
        }
        this.stack.batchUpdate(false);
        for (const val of this.vals.children) {
            const stackItem = this.stackItems[`elem_${val.id}`];
            if (stackItem) stackItem.reRender(false, val.h, val.w);
        }
        this.disableChange();
    }

    disableChange() {
        this.state.change = false;
    }

    onChange() {
        this.state.change = true;
    }

    onBack() {
        browser.history.go(-1);
    }

    gridValues(item) {
        const scale = this.gridScale || 5;
        const threshold = scale * 2 - 1;
        const sheetPosition = item.dashboard_sheet_option_ids;

        const minH = item.type === 'kpi' ? (item.kpi_target ? 2 : 1) : 3;
        const minW = item.type === 'kpi' ? 3 : 3;

        let w = minW, h = minH, x = 0, y = 0;

        if (sheetPosition.length) {
            ({graph_height: h, graph_width: w, x, y} = sheetPosition[0].attributes);
            x = x || 0;
            y = y || 0;
            if (h > threshold) {
                h = Math.max(1, Math.round(h / scale));
                y = Math.round(y / scale);
            }
        }

        return {
            id: item.id, x, y,
            w: Math.max(w || minW, minW),
            h: Math.max(h || minH, minH),
            minW, minH,
        };
    }

    _warmUpDrag() {
        const container = this.ref.el;
        if (!container) return;
        const item = container.querySelector('.grid-stack-item');
        if (!item) return;
        this.stack.off('change');
        const rect = item.getBoundingClientRect();
        const x = Math.round(rect.left + rect.width / 2);
        const y = Math.round(rect.top + rect.height / 2);
        const ev = (type, cx, cy, buttons) => new MouseEvent(type, {
            bubbles: true, cancelable: true,
            clientX: cx, clientY: cy,
            screenX: cx, screenY: cy,
            buttons, button: 0, view: window,
        });
        item.dispatchEvent(ev('mousedown', x, y, 1));
        document.dispatchEvent(ev('mousemove', x + 4, y + 4, 1));
        document.dispatchEvent(ev('mouseup', x + 4, y + 4, 0));
        setTimeout(() => {
            this.state.change = false;
            this.vals = this.stack.save(false, true);
            this.stack.on('change', this.onChange.bind(this));
        }, 100);
    }

    dragStop(event, el) {
        Object.values(this.stackItems).forEach(item => {
            if (item.resizeObserver && item.el) item.resizeObserver.observe(item.el);
            if (item.eChart) item.eChart.resize();
        });
        // KPI items need a reRender nudge after drag to fix layout
        if (this.stackItems[el.id] instanceof StackKpiItem) {
            this.stackItems[el.id].reRender(false, 1, 3);
        }
    }
}

EditDashboard.template = "cyllo_analytics.EditDashboard";
registry.category("actions").add("edit_dashboard", EditDashboard);
