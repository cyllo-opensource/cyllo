/** @odoo-module **/
import {
    odooExceptionTitleMap,
    WarningDialog,
    RedirectWarningDialog,
    ErrorDialog,
    ClientErrorDialog,
    NetworkErrorDialog,
    RPCErrorDialog,
    SessionExpiredDialog,
} from "@web/core/errors/error_dialogs";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { _lt, _t } from "@web/core/l10n/translation";
import { useState } from "@odoo/owl";
import { session } from "@web/session";
import { annotateTraceback } from "@web/core/errors/error_utils";


// Constants
const REPORT_GROUP = "cyllo_issue_reporting.group_error_reporting_user";
const MAX_TRACEBACK_LENGTH = 100000;
const PERMISSION_TIMEOUT_MS = 3000;
const QWEB_ERROR_RE = /QWebException|Error while render(?:ing)? the template/;
// Exact addon frame (debug=assets or source-mapped): /my_module/static/src/js/x.js:12:3
const JS_FRAME_RE = /(?:@|\/)(\w+)\/(static\/[^\s():]+):(\d+)(?::\d+)?/g;
// Frame inside a bundle: https://host/web/assets/<hash>/web.assets_web.min.js:2892:45
const BUNDLE_FRAME_RE = /(https?:\/\/[^\s()]+?\/web\/assets\/[^\s()]+?\.js):(\d+):(\d+)/g;
// File headers Odoo writes into every bundle, before each concatenated file
const HEADER_MIN_RE = /^\/\*\s+(\/[^\s*]+\/static\/[^\s*]+\.js)\s+\*\/\s*$/; // /* /mod/static/x.js */
const HEADER_DEBUG_RE = /^\*\s+Filepath:\s+(\/\S+\.js)\s*\*?\s*$/; // debug bundles
// Owl wraps the real error: "... Caused by: TypeError ..."
const CAUSE_SPLIT_RE = /\n\s*Caused by:\s*/i;
const bundleCache = new Map(); // bundle url -> lines[] (max 2 entries)

/**
 * Custom titles for error dialogs
 */
ErrorDialog.title = _lt("System Error");
ClientErrorDialog.title = _lt("System Client Error");
SessionExpiredDialog.title = _lt("System Session Expired");
NetworkErrorDialog.title = _lt("System Network Error"); // was "Expired" (typo)

// Permission check: must NEVER block or break an error dialog

let reportPermission = null;
let reportInFlight = false; // guards double clicks on the Report button

/**
 * Resolves to true/false. Never rejects and never hangs: when the server is
 * down (network error dialog) or the session is gone (session expired), the
 * hasGroup RPC would fail/hang and, inside onWillStart, that would break the
 * error dialog itself.
 */
function checkReportPermission(userService) {
    if (!session.is_issue_reporting) {
        return Promise.resolve(false);
    }
    if (!reportPermission) {
        reportPermission = Promise.race([
            Promise.resolve().then(() => userService.hasGroup(REPORT_GROUP)),
            new Promise((resolve) => setTimeout(() => resolve(false), PERMISSION_TIMEOUT_MS)),
        ])
            .then(Boolean)
            .catch(() => false)
            .then((allowed) => {
                if (!allowed) {
                    reportPermission = null; // retry next time (failure/timeout)
                }
                return allowed;
            });
    }
    return reportPermission;
}

// Source location helpers (work with debug OFF, =1 or =assets; never touch debug)

function withTimeout(promise, ms) {
    return Promise.race([promise, new Promise((resolve) => setTimeout(() => resolve(null), ms))]);
}

async function getBundleLines(url) {
    if (bundleCache.has(url)) {
        return bundleCache.get(url);
    }
    try {
        // Same URL the page already loaded => normally served from the HTTP cache
        const res = await withTimeout(fetch(url, { credentials: "same-origin" }), 5000);
        if (!res || !res.ok) {
            return null;
        }
        const lines = (await res.text()).split("\n");
        if (bundleCache.size >= 2) {
            bundleCache.delete(bundleCache.keys().next().value);
        }
        bundleCache.set(url, lines);
        return lines;
    } catch (e) {
        return null;
    }
}

/** Nearest file header above a bundle line => original file path (+ code snippet). */
async function locateInBundle(url, line, col) {
    const lines = await getBundleLines(url);
    if (!lines || line < 1 || line > lines.length) {
        return null;
    }
    for (let i = line - 1; i >= 0; i--) {
        const text = lines[i];
        if (text.length > 300) {
            continue; // code line, cannot be a header
        }
        const m = text.match(HEADER_MIN_RE) || text.match(HEADER_DEBUG_RE);
        if (m) {
            const code = lines[line - 1] || "";
            const start = Math.max(0, col - 1 - 50);
            return { path: m[1], snippet: code.slice(start, col - 1 + 50) };
        }
    }
    return null;
}

/** Whitespace/comment-insensitive search of the snippet in the raw source file. */
async function guessOriginalLine(path, snippet) {
    const needle = snippet.replace(/\s+/g, "");
    if (needle.length < 12) {
        return null;
    }
    try {
        const res = await withTimeout(fetch(path, { credentials: "same-origin" }), 5000);
        if (!res || !res.ok) {
            return null;
        }
        // strip comments but keep newlines so line numbers stay valid
        const raw = (await res.text()).replace(/\/\*[\s\S]*?\*\/|\/\/[^\n]*/g, (m) =>
            m.replace(/[^\n]/g, "")
        );
        let stripped = "";
        const lineOf = [];
        let line = 1;
        for (const ch of raw) {
            if (ch === "\n") {
                line++;
            } else if (!/\s/.test(ch)) {
                stripped += ch;
                lineOf.push(line);
            }
        }
        const first = stripped.indexOf(needle);
        if (first === -1 || stripped.indexOf(needle, first + 1) !== -1) {
            return null; // not found or ambiguous: better no line than a wrong one
        }
        return lineOf[first + Math.floor(needle.length / 2)];
    } catch (e) {
        return null;
    }
}

/** Frames of the DEEPEST cause first (Owl wraps the real error). */
function* causeFrames(traceback, regex) {
    for (const block of traceback.split(CAUSE_SPLIT_RE).reverse()) {
        yield* block.matchAll(regex);
    }
}

/** Exact addon frame already present in the traceback (debug=assets / source maps). */
function findAddonFrame(traceback) {
    for (const m of causeFrames(traceback, JS_FRAME_RE)) {
        const [, mod, path, line] = m;
        if (mod !== "web" && !path.includes("static/lib/")) {
            return { module: mod, location: `${mod}/${path}:${line}`, note: "" };
        }
    }
    return null;
}

/** Bundle frame => original addon file, through the bundle's file headers. */
async function resolveBundleFrames(traceback) {
    let tried = 0;
    for (const m of causeFrames(traceback, BUNDLE_FRAME_RE)) {
        if (++tried > 8) {
            break;
        }
        const [, url, line, col] = m;
        const hit = await locateInBundle(url, Number(line), Number(col));
        if (!hit) {
            continue;
        }
        const rel = hit.path.slice(1); // "my_module/static/src/js/x.js"
        const mod = rel.split("/")[0];
        if (mod === "web" || rel.includes("/static/lib/")) {
            continue; // framework / library frame: keep looking
        }
        const origLine = await guessOriginalLine(hit.path, hit.snippet);
        return {
            module: mod,
            location: origLine ? `${rel}:${origLine}` : rel,
            note: `[Source resolved from bundle ${url}:${line}:${col}${origLine ? "" : " (line unknown)"}]\n`,
        };
    }
    return null;
}

/**
 * Resolve source maps and extract the original source location.
 * @param {Object} props dialog props
 * @param {string} defaultTraceback
 * @param {string} [forcedType] e.g. "warning" for UserError/ValidationError dialogs
 */
async function resolveErrorMetadata(props, defaultTraceback, forcedType) {
    let traceback = defaultTraceback || "";
    let fileLocation = "";
    let moduleName = "";
    let errorType = "frontend";

    const debugInfo = props && props.data && props.data.debug;
    const isPythonTraceback =
        traceback.includes("Traceback (most recent call last):") || Boolean(debugInfo);

    if (isPythonTraceback) {
        errorType = "backend";
        if (debugInfo) {
            traceback = debugInfo;
        }
        // XML / View ParseError, or QWeb render error (location resolved server side)
        const xmlMatch =
            traceback.match(/while parsing\s+([^\s,:]+\.(?:xml|csv))(?::(\d+))?/i) ||
            traceback.match(
                /View error context:[\s\S]*?'file':\s*['"]([^'"]+)['"](?:[\s\S]*?'line':\s*(\d+))?/i
            );
        if (xmlMatch) {
            errorType = "xml";
            const rawPath = xmlMatch[1].replace(/\\/g, "/");
            const lineNo = xmlMatch[2];
            const modMatch = rawPath.match(
                /(?:addons[\w-]*|odoo\/addons|custom_addons)\/([^/]+)\/(.+)$/
            );
            if (modMatch) {
                moduleName = modMatch[1];
                fileLocation = `${modMatch[1]}/${modMatch[2]}${lineNo ? `:${lineNo}` : ""}`;
            } else {
                fileLocation = lineNo ? `${rawPath}:${lineNo}` : rawPath;
            }
        } else if (QWEB_ERROR_RE.test(traceback)) {
            errorType = "xml";
        }
    } else {
        // Frontend JS error.
        // 1) Odoo's own source-map annotation (helps when the bundle has a map), bounded.
        const errorObj = props && (props.error || (props.data && props.data.error));
        try {
            if (errorObj instanceof Error) {
                traceback = (await withTimeout(annotateTraceback(errorObj), 4000)) || traceback;
            } else if (traceback && !traceback.includes("(")) {
                const fake = new Error(props && props.message ? props.message : "Client Error");
                fake.stack = traceback;
                traceback = (await withTimeout(annotateTraceback(fake), 4000)) || traceback;
            }
        } catch (e) {
            // keep the original traceback
        }

        // 2) exact file URLs (debug=assets / source-mapped), else
        // 3) bundle file headers (works in any debug mode, incl. no debug).
        const found = findAddonFrame(traceback) || (await resolveBundleFrames(traceback));
        if (found) {
            moduleName = found.module;
            fileLocation = found.location;
            traceback = found.note + traceback;
        }
    }

    if (forcedType) {
        errorType = forcedType;
    }
    if (traceback.length > MAX_TRACEBACK_LENGTH) {
        traceback = traceback.slice(0, MAX_TRACEBACK_LENGTH) + "\n... [truncated]";
    }
    return { traceback, fileLocation, moduleName, errorType };
}

// Shared patch factory

/**
 * Returns a FRESH patch object each call. Sharing one object between several
 * patch() calls (as the spread in the old RPCErrorDialog patch did) is unsafe:
 * `super` inside object-literal methods is bound to the literal where the
 * method was written, so it can resolve to the wrong class.
 */
function makeReportPatch({ actionName, fallbackName, forcedType }, extraMethods = {}) {
    const patchObject = {
        setup() {
            super.setup();
            this.userService = useService("user");
            // ErrorDialog/RPCErrorDialog already own `this.state` (showTraceback):
            // extend it instead of replacing it.
            if (this.state) {
                this.state.canReportAdmin = false;
            } else {
                this.state = useState({ canReportAdmin: false });
            }
            // Fire and forget: the dialog must render immediately.
            checkReportPermission(this.userService).then((allowed) => {
                this.state.canReportAdmin = allowed;
            });
        },

        _getReportMessage() {
            const props = this.props || {};
            return (
                this.message ||
                props.message ||
                (props.data && props.data.message) ||
                (props.data && props.data.arguments && props.data.arguments[0]) ||
                ""
            );
        },

        async onClickReportAdmin() {
            console.debug("[error-report] Report button clicked");
            if (reportInFlight) {
                return; // double click
            }
            reportInFlight = true;
            try {
                await this._reportToAdmin();
            } finally {
                reportInFlight = false;
            }
        },

        async _reportToAdmin() {
            const { action: actionService, notification } = this.env.services;
            const props = this.props || {};
            let rawTraceback = this.traceback || "";
            if (!rawTraceback) {
                rawTraceback =
                    props.traceback ||
                    (props.data && props.data.debug) ||
                    (props.error && props.error.stack) ||
                    "";
            }

            let meta;
            try {
                meta = await resolveErrorMetadata(props, rawTraceback, forcedType);
            } catch (e) {
                meta = {
                    traceback: String(rawTraceback),
                    fileLocation: "",
                    moduleName: "",
                    errorType: forcedType || "frontend",
                };
            }
            const message = this._getReportMessage();
            const name = String(this.title || this.constructor.title || props.name || fallbackName);

            if (props.close) {
                props.close();
            }

            try {
                await actionService.doAction({
                    type: "ir.actions.act_window",
                    name: String(actionName),
                    res_model: "error.report.wizard",
                    view_mode: "form",
                    views: [[false, "form"]],
                    target: "new",
                    context: {
                        default_name: name,
                        default_error_message: String(message),
                        default_traceback: meta.traceback,
                        default_url: window.location.href,
                        default_module_name: meta.moduleName || undefined, // resolved JS module
                        default_file_location: meta.fileLocation || undefined, // resolved JS file[:line]
                        default_error_type: meta.errorType,
                    },
                });
            } catch (e) {
                // Never raise a new error dialog from the "report" button itself
                console.error("Could not open the error report form:", e);
                notification.add(_t("The error report form could not be opened."), {
                    type: "danger",
                });
            }
        },
    };
    // Extra methods must NOT use `super` (they are copied, not defined in the literal).
    return Object.assign(patchObject, extraMethods);
}

// 1. ErrorDialog (covers ClientErrorDialog, NetworkErrorDialog)

patch(
    ErrorDialog.prototype,
    makeReportPatch({
        actionName: _lt("Report Error to Administrator"),
        fallbackName: _lt("Client Error"),
    })
);

// 2. RPCErrorDialog (server / Python / RPC errors)

patch(
    RPCErrorDialog.prototype,
    makeReportPatch(
        {
            actionName: _lt("Report Error to Administrator"),
            fallbackName: _lt("Server Error"),
        },
        {
            inferTitle() {
                if (this.props.exceptionName && odooExceptionTitleMap.has(this.props.exceptionName)) {
                    this.title = odooExceptionTitleMap.get(this.props.exceptionName).toString();
                    return;
                }
                if (!this.props.type) {
                    return;
                }
                switch (this.props.type) {
                    case "server":
                        this.title = _t("System Server Error");
                        break;
                    case "script":
                        this.title = _t("System Client Error");
                        break;
                    case "network":
                        this.title = _t("System Network Error");
                        break;
                }
            },
        }
    )
);


// 3. WarningDialog (UserError, ValidationError, AccessError, MissingError...)

patch(
    WarningDialog.prototype,
    makeReportPatch(
        {
            actionName: _lt("Report Warning to Administrator"),
            fallbackName: _lt("Warning"),
            forcedType: "warning",
        },
        {
            inferTitle() {
                if (this.props.exceptionName && odooExceptionTitleMap.has(this.props.exceptionName)) {
                    return odooExceptionTitleMap.get(this.props.exceptionName).toString();
                }
                return this.props.title || _t("Cyllo Warning");
            },
        }
    )
);

// 4. RedirectWarningDialog (odoo.exceptions.RedirectWarning: "Go to settings",
//    "Configure mail server"...). Was not covered at all before.

if (RedirectWarningDialog) {
    patch(
        RedirectWarningDialog.prototype,
        makeReportPatch({
            actionName: _lt("Report Warning to Administrator"),
            fallbackName: _lt("Redirect Warning"),
            forcedType: "warning",
        })
    );
}


