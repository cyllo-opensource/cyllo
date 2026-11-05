/** @odoo-module **/
import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";

/**
 * Screen-blocker back button (companion of cyllo_screen_block.scss).
 *
 * A blocked client action is a dead end by design. On `current` targets that
 * is survivable: the navbar, breadcrumbs and the phone's "hamburger" all stay
 * usable, so the user has a way out. On `target: "fullscreen"` the action
 * manager strips the whole frame (webclient only renders the action, see
 * webclient.xml's `!state.fullscreen` guard) — without help the veil is a
 * lock with no key.
 *
 * This service floats a single "go back" button into the blocked root, and
 * only when it is needed: the client is fullscreen AND at least one root
 * carrying the blocker class is on screen. Anything below 992px shows it
 * (styled by the utility's media queries — the same range the veil covers),
 * so plain CSS decides when the button is visible.
 *
 * Going back reuses Odoo's own controller history slot via the current
 * controller's config (`historyBack`), falling back to the browser history —
 * the same semantics as the first breadcrumb click.
 */

const BLOCKED_ROOT_SELECTOR = ".cy_hide_mobile_screen, .cy_hide_small_screen";
const BACK_BUTTON_SELECTOR = ".cy_screen_block_back";

function goBack(env) {
    const controller = env.services.action?.currentController;
    if (controller?.config?.historyBack) {
        controller.config.historyBack();
    } else {
        browser.history.back();
    }
}

/** The pill is icon-only — ::before carries the remixicon glyph. */
function buildBackButton(env) {
    const button = document.createElement("div");
    button.className = "cy_screen_block_back";
    button.setAttribute("role", "button");
    button.setAttribute("aria-label", "Go back");
    button.title = "Go Back";
    button.addEventListener("click", () => goBack(env));
    return button;
}

export const cyScreenBlockService = {
    dependencies: [],

    start(env) {
        let isFullscreen = false;

        function sync() {
            if (!isFullscreen) {
                for (const button of document.querySelectorAll(BACK_BUTTON_SELECTOR)) {
                    button.remove();
                }
                return;
            }
            // Only the outermost blocked roots host a button: a nested
            // carrier div would render a second identical pill inside the
            // first one's covered area.
            const blockedRoots = [
                ...document.querySelectorAll(BLOCKED_ROOT_SELECTOR),
            ].filter((root) => !root.parentElement?.closest(BLOCKED_ROOT_SELECTOR));
            for (const root of blockedRoots) {
                if (root.querySelector(BACK_BUTTON_SELECTOR)) {
                    continue;
                }
                const button = buildBackButton(env);
                root.appendChild(button);
            }
        }

        let scheduled = 0;
        function scheduleSync() {
            if (scheduled) {
                return;
            }
            scheduled = browser.requestAnimationFrame(() => {
                scheduled = 0;
                sync();
            });
        }

        // The webclient keeps its true frame flag; the bus event carries the
        // action mode directly ("fullscreen" | "current" | "new" | ...).
        env.bus.addEventListener("ACTION_MANAGER:UI-UPDATED", (mode) => {
            isFullscreen = mode === "fullscreen";
            scheduleSync();
        });
        // Crossing a breakpoint without a UI update still changes what the
        // blocker shows, so follow the ui service's resize broadcast too.
        env.bus.addEventListener("resize", scheduleSync);
        // OWL re-renders rebuild the blocked root's children and would drop
        // the pill; re-assert it whenever the tree shifts.
        const observer = new MutationObserver(scheduleSync);
        observer.observe(document.body, {
            childList: true,
            subtree: true,
        });
    },
};

registry.category("services").add("cy_screen_block", cyScreenBlockService);
