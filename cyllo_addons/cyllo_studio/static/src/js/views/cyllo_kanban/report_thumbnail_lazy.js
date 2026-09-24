/** @odoo-module **/

/**
 * Lazy report thumbnail generation.
 *
 * The report kanban (ir.actions.report, js_class="n_kanban") shows a
 * placeholder image until `report_thumbnail` is set. Generating a thumbnail
 * means rendering a full QWeb PDF and converting it to an image server-side,
 * which is expensive. Instead of generating every missing thumbnail up
 * front, this patches the stock KanbanRecord so each report card only
 * requests its thumbnail once it actually scrolls into view, and never
 * asks again in the same session if the report has no records to render.
 */
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { KanbanRecord } from "@web/views/kanban/kanban_record";
import { onMounted, onWillUnmount } from "@odoo/owl";

const SKIP_KEY = "cyllo_report_thumbnail_skip";

function getSkipSet() {
    try {
        return new Set(JSON.parse(sessionStorage.getItem(SKIP_KEY) || "[]"));
    } catch {
        return new Set();
    }
}

function addSkip(reportId) {
    const skip = getSkipSet();
    skip.add(reportId);
    sessionStorage.setItem(SKIP_KEY, JSON.stringify([...skip]));
}

patch(KanbanRecord.prototype, {
    setup() {
        super.setup();
        if (this.props.record.resModel !== "ir.actions.report") {
            return;
        }
        this.thumbnailRpc = useService("rpc");
        let observer = null;
        onMounted(() => {
            const record = this.props.record;
            const reportId = record.resId;
            if (!reportId || record.data.report_thumbnail || getSkipSet().has(reportId)) {
                return;
            }
            const img = this.rootRef.el?.querySelector(".cyllo_report_thumbnail_wrapper img");
            if (!img) {
                return;
            }
            observer = new IntersectionObserver(
                (entries) => {
                    if (!entries[0].isIntersecting) {
                        return;
                    }
                    observer.disconnect();
                    this.thumbnailRpc("/cyllo_studio/generate_report_thumbnail", { report_id: reportId })
                        .then((res) => {
                            if (res && res.success) {
                                img.src = `/web/image/ir.actions.report/${reportId}/report_thumbnail?unique=${Date.now()}`;
                            } else {
                                addSkip(reportId);
                            }
                        })
                        .catch(() => addSkip(reportId));
                },
                { rootMargin: "150px", threshold: 0.1 }
            );
            observer.observe(this.rootRef.el);
        });
        onWillUnmount(() => observer && observer.disconnect());
    },
});