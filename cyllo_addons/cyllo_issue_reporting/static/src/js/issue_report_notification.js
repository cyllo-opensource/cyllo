/** @odoo-module **/
import { registry } from "@web/core/registry";
import { markup } from "@odoo/owl";
import { escape } from "@web/core/utils/strings";

function issueReportNotification(env, action) {
    const params = action.params || {};
    const { title, message = "", issue_id, issue_ref, sticky } = params;
    const issueId = parseInt(issue_id, 10);
    const hasValidIssue = !isNaN(issueId) && issueId > 0 && issue_ref;

    let content;
    if (hasValidIssue) {
        content = markup(
            `${escape(message)} ` +
            `(<a href="#" class="o_issue_report_link fw-bold text-decoration-underline" ` +
            `data-issue-id="${issueId}">${escape(String(issue_ref))}</a>)`
        );
    } else {
        content = escape(message);
    }

    env.services.notification.add(content, {
        title: title || "",
        type: "success",
        sticky: sticky !== undefined ? Boolean(sticky) : true,
    });

    // Returning `next` lets the framework close the wizard dialog.
    return params.next;
}

registry.category("actions").add("issue_report_notification", issueReportNotification);

// The form view opens ONLY when the reference link is clicked.
registry.category("services").add("issue_report_link_handler", {
    dependencies: ["action"],
    start(env, { action }) {
        document.addEventListener("click", (ev) => {
            const link = ev.target.closest("a.o_issue_report_link");
            if (!link) {
                return;
            }
            ev.preventDefault();

            const issueId = parseInt(link.dataset.issueId, 10);
            if (isNaN(issueId) || issueId <= 0) {
                return;
            }

            // Prevent rapid duplicate clicks
            link.style.pointerEvents = "none";

            // Dismiss the notification toast upon click
            const notifEl = link.closest(".o_notification");
            if (notifEl) {
                const closeBtn = notifEl.querySelector(".o_notification_close");
                if (closeBtn) {
                    closeBtn.click();
                }
            }

            action.doAction({
                type: "ir.actions.act_window",
                res_model: "issue.report",
                res_id: issueId,
                views: [[false, "form"]],
                target: "current",
            });
        });
    },
});
