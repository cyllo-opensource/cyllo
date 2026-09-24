/** @odoo-module **/

/** @odoo-module **/

/**
 * Cyllo Studio Custom Form Compiler
 *
 * This module extends Odoo's default FormCompiler to provide advanced
 * compilation for form views in Cyllo Studio. It enhances Odoo forms
 * with:
 *
 * 1. Support for invisible nodes with session-based visibility toggling.
 * 2. Dynamic handling of labels, including FormLabel component generation.
 * 3. Compilation of groups, outer/inner groups, and slots with colspan.
 * 4. Sheet compilation with avatars, ribbons, badges, and children elements.
 * 5. Notebook compilation with pages, anchors, default page selection,
 *    and invisible page handling.
 * 6. ButtonBox compilation with slot-based buttons, visibility rules,
 *    and automatic string extraction for status labels.
 * 7. Chatter component compilation for activity, followers, and message lists.
 * 8. Automatic cy-xpath injection for automated testing purposes.
 *
 * Helper functions included in this module:
 * - objectToString: Converts a JS object to string for QWeb props.
 * - appendAttf: Appends a string to a t-attf attribute.
 * - appendToExpr: Appends a string to a QWeb expression.
 * - XpathExtract: Extracts XPath-like paths for elements.
 * - compileChatter: Compiles the chatter component for form views.
 *
 * This compiler is designed to integrate seamlessly with the Cyllo Studio
 * environment and enhance the default Odoo form rendering capabilities.
 */

import { FormCompiler } from "@web/views/form/form_compiler";
import { SIZES } from "@web/core/ui/ui_service";
import { InnerGroup, OuterGroup, Group } from "@web/views/form/form_group/form_group";
import { toStringExpression } from "@web/views/utils";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { evaluateExpr } from "@web/core/py_js/py";

import {
    append,
    combineAttributes,
    createElement,
    createTextNode,
    getTag,
    setAttributes,
} from "@web/core/utils/xml";
import {
    copyAttributes,
    getModifier,
    isComponentNode,
    isTextNode,
    makeSeparator,
} from "@web/views/view_compiler";


/**
 * @param {Record<string, any>} obj
 * @returns {string}
 */
export function objectToString(obj) {
    return `{${Object.entries(obj)
        .map((t) => t.join(":"))
        .join(",")}}`;
}
function appendAttf(el, attr, string) {
    const attrKey = `t-attf-${attr}`;
    const attrVal = el.getAttribute(attrKey);
    el.setAttribute(attrKey, appendToExpr(attrVal, string));
}
//
function appendToExpr(expr, string) {
    const re = /{{.*}}/;
    const oldString = re.exec(expr);
    return oldString ? `${oldString} {{${string} }}` : `{{${string} }}`;
}

function XpathExtract(el, tag) {
    var parser = new DOMParser();
    var xmlDoc = parser.parseFromString(el.outerHTML, "text/xml");
    var elements = xmlDoc.evaluate(tag, xmlDoc, null, XPathResult.ANY_TYPE, null);
    var element = elements.iterateNext();
    var xpath = '';
    for (; element && element.nodeType == 1; element = element.parentNode) {
        var id = element.getAttribute('id');
        if (id) {
            xpath = '[@id="' + id + '"]' + xpath;
            break;
        }

        var nodeName = element.nodeName.toLowerCase();
        var parent = element.parentNode;
        var siblings = parent.childNodes;
        var count = 0;
        for (var i = 0; i < siblings.length; i++) {
            var sibling = siblings[i];
            if (sibling.nodeType == 1 && sibling.nodeName.toLowerCase() == nodeName) {
                count++;
            }
            if (sibling == element) {
                xpath = '/' + nodeName + '[' + count + ']' + xpath;
                break;
            }
        }
    }
    return xpath

}
function compileChatter(node, params) {
    let hasActivities = false;
    let hasFollowers = false;
    let hasMessageList = false;
    let hasParentReloadOnAttachmentsChanged;
    let hasParentReloadOnFollowersUpdate = false;
    let hasParentReloadOnMessagePosted = false;
    let isAttachmentBoxVisibleInitially = false;
    for (const childNode of node.children) {
        const options = evaluateExpr(childNode.getAttribute("options") || "{}");
        switch (childNode.getAttribute("name")) {
            case "activity_ids":
                hasActivities = true;
                break;
            case "message_follower_ids":
                hasFollowers = true;
                hasParentReloadOnFollowersUpdate = Boolean(options["post_refresh"]);
                isAttachmentBoxVisibleInitially =
                    isAttachmentBoxVisibleInitially || Boolean(options["open_attachments"]);
                break;
            case "message_ids":
                hasMessageList = true;
                hasParentReloadOnAttachmentsChanged = options["post_refresh"] === "always";
                hasParentReloadOnMessagePosted = Boolean(options["post_refresh"]);
                isAttachmentBoxVisibleInitially =
                    isAttachmentBoxVisibleInitially || Boolean(options["open_attachments"]);
                break;
        }
    }
    const chatterContainerXml = createElement("t");
    const path = node.getAttribute('cy-xpath')

    setAttributes(chatterContainerXml, {
        "t-component": "__comp__.mailComponents.Chatter",
        hasActivities,
        hasFollowers,
        hasMessageList,
        hasParentReloadOnAttachmentsChanged,
        hasParentReloadOnFollowersUpdate,
        hasParentReloadOnMessagePosted,
        isAttachmentBoxVisibleInitially,
        threadId: "__comp__.props.record.resId or undefined",
        threadModel: "__comp__.props.record.resModel",
        webRecord: "__comp__.props.record",
        saveRecord: "() => __comp__.save and __comp__.save()",
        cyXpath: toStringExpression(path),

    });
    const chatterContainerHookXml = createElement("div");
    chatterContainerHookXml.classList.add("o-mail-ChatterContainer", "o-mail-Form-chatter");
    append(chatterContainerHookXml, chatterContainerXml);
    return chatterContainerHookXml;
}

const chatterRegistry = registry.category("form_compilers")
const chatterCompiler = chatterRegistry.get('chatter_compiler')
chatterCompiler.fn = compileChatter
chatterRegistry.add("chatter_compiler", chatterCompiler, { force: true });



/**
 * Marker class Studio puts on a group the user removed from the view.
 *
 * The node is NOT deleted from the arch: fields inside it may still be
 * referenced by other nodes' `context`/`domain`, and dropping them makes
 * ir.ui.view refuse the whole edit ("Field 'x' used in context ... is
 * restricted to the group(s) ..."). It is hidden instead — `invisible="1"`
 * takes care of end users, this class takes care of the editor.
 */
export const STUDIO_HIDDEN_CLASS = "cy-studio-hidden";

/**
 * Tell whether an arch node was removed-by-hiding in Studio.
 *
 * @param {Element|null} node - Arch node.
 * @returns {boolean}
 */
function isStudioHidden(node) {
    if (!node || node.nodeType !== 1) {
        return false;
    }
    return (node.getAttribute("class") || "").split(/\s+/).includes(STUDIO_HIDDEN_CLASS);
}

/**
 * Tell whether an arch node is a ribbon container (`<div class="ribbon ...">`).
 *
 * @param {Element|null} node - Arch node.
 * @returns {boolean}
 */
function isRibbonNode(node) {
    if (!node || node.nodeType !== 1 || getTag(node, true) !== "div") {
        return false;
    }
    return (node.getAttribute("class") || "").split(/\s+/).includes("ribbon");
}

/**
 * Tell whether an arch node lives inside a ribbon container. Ribbons are edited
 * through the RibbonDialog wizard, so the nodes they wrap (typically the
 * `<span>` holding the label) must not be wired to the text/span editors.
 *
 * @param {Element|null} node - Arch node.
 * @returns {boolean}
 */
function isInsideRibbon(node) {
    let parent = node && node.parentElement;
    while (parent) {
        if (isRibbonNode(parent)) {
            return true;
        }
        parent = parent.parentElement;
    }
    return false;
}

/**
 * Tell whether an arch node lives inside a <button> (regular or smart button).
 *
 * Buttons are edited through ViewButton.onClick, which opens the Button /
 * Smart Button properties panel and already exposes the label (compileButtonBox
 * computes `stringPath` for exactly that). Their inner nodes must therefore not
 * be wired to the text/span editors, for two reasons:
 *
 *  1. `handleSelectSpan`/`onSpanClick` live on CylloFormRenderer, but the button
 *     box is compiled a second time by the FormController and rendered in the
 *     control panel with `__comp__` bound to the *controller*
 *     (see web form_controller.js `useViewCompiler({ButtonBox: …})` and
 *     form_controller.xml's `t-call-context`). There the handlers do not exist,
 *     so clicking a smart button label threw
 *     "__comp__.handleSelectSpan is not a function".
 *  2. `handleSelectSpan` calls stopPropagation(), so even where it resolved it
 *     swallowed the click and the Smart Button properties never opened.
 *
 * @param {Element|null} node - Arch node.
 * @returns {boolean}
 */
function isInsideButton(node) {
    // Same set of nodes ViewCompiler routes to compileButton (i.e. that end up
    // as a <ViewButton> with their body in its `contents` slot).
    const isButtonNode = (el) => {
        if (el.hasAttribute("data-bs-toggle")) {
            return false;
        }
        const tag = getTag(el, true);
        return tag === "button" ||
            (tag === "a" && (el.hasAttribute("type") || el.hasAttribute("data-type")));
    };
    let parent = node && node.parentElement;
    while (parent) {
        if (isButtonNode(parent)) {
            return true;
        }
        parent = parent.parentElement;
    }
    return false;
}

export class CylloFormCompiler extends FormCompiler {
    setup() {
        super.setup();
        this.rpc = useService("rpc");
    }
    /**
     * Compile a generic node.
     * Adds handling for invisible nodes, stripes, dynamic click events, and field extraction.
     * @param {Element} node - The node to compile.
     * @param {Record<string, any>} params - Compilation parameters.
     * @param {boolean} evalInvisible - Whether to evaluate invisible nodes.
     * @returns {Element} - Compiled node.
     */
    compileNode(node, params = {}, evalInvisible = false) {
        if (isStudioHidden(node)) {
            return;
        }
        const invisible_session = sessionStorage.getItem('invisible');
        //        if (invisible_session) {
        evalInvisible = false;
        //        }
        let compiledNode = super.compileNode(node, params, evalInvisible);
        if (!compiledNode) {
            return compiledNode;
        }
        const insideRibbon = isInsideRibbon(node);
        const ownsOwnClick = insideRibbon || isInsideButton(node);
        if (node.nodeType === 1) {
            const invisible = getModifier(node, "invisible");

            if (invisible && invisible !== "False" && invisible !== "0") {
                let isVisibleExpr;
                if (invisible === "True" || invisible === "1") {
                    isVisibleExpr = "false";
                } else {
                    isVisibleExpr = `!__comp__.evaluateBooleanExpr(${JSON.stringify(
                        invisible
                    )}, __comp__.props.record.evalContextWithVirtualIds)`;
                }
                //                compiledNode.setAttribute("t-if", isVisibleExpr);
                const fieldTag = getTag(node, true);
                const isButton = fieldTag === "button" ||
                    compiledNode.tagName.toLowerCase() === "button" ||
                    compiledNode.tagName === "ViewButton";
                const isSmartButton = compiledNode.tagName === "SmartButton" ||
                    node.classList?.contains("oe_stat_button") ||
                    node.classList?.contains("btn");

                // Apply t-if ONLY if it's NOT a button or smart button
                if (!isButton && !isSmartButton) {
                    compiledNode.setAttribute("t-if", isVisibleExpr);
                }
                if (isComponentNode(compiledNode)) {
                    compiledNode.setAttribute('striped', `!${isVisibleExpr}`)
                } else {
                    const currentClass = compiledNode.getAttribute("t-att-class") || "";
                    const stripedClass = `(!${isVisibleExpr}) ? 'cy-studio-striped' : ''`;

                    if (currentClass) {
                        compiledNode.setAttribute("t-att-class", `${currentClass} + ' ' + (${stripedClass})`);
                    } else {
                        compiledNode.setAttribute("t-att-class", stripedClass);
                    }
                }
            }

            if (isRibbonNode(node)) {
                compiledNode.setAttribute("t-on-click", `(ev)=>__comp__.onRibbonClick(ev)`);
            }

            if (getTag(node, true) === "span") {
                if (!ownsOwnClick) {
                    const spanInvisible = toStringExpression(node.getAttribute('invisible') || '0')
                    compiledNode.setAttribute("t-on-click", `(ev)=>__comp__.onSpanClick(ev, ${spanInvisible})`)
                }
                // Striping stays in all contexts: evaluateBooleanExpr and
                // props.record exist on the renderer *and* on the controller.
                compiledNode.setAttribute("t-att-class", `__comp__.evaluateBooleanExpr(${JSON.stringify(
                    getModifier(node, "invisible")
                )}, __comp__.props.record.evalContextWithVirtualIds)
                ? 'cy-studio-striped' : ''`)
            }
        }
        const validAttributes = ["t-out", "t-esc"];
        if (compiledNode?.attributes) {
            const AttrArray = Array.from(compiledNode.attributes);
            const hasValidAttribute = validAttributes.some(attr =>
                AttrArray.some(nodeAttr => nodeAttr.name === attr)
            );
            if (!ownsOwnClick && compiledNode.tagName.toLowerCase() === 'span' && !compiledNode.children.length > 0) {
                compiledNode.setAttribute("t-on-click", `(el)=>__comp__.handleSelectSpan(el)`);
            }
            if (hasValidAttribute) {
                AttrArray.forEach(nodeAttr => {
                    if (validAttributes.includes(nodeAttr.name)) {
                        const match = nodeAttr.value.match(/record\.([^.]+)\.value/);
                        if (match) {
                            const extractedValue = match[1];
                            compiledNode.setAttribute('name', extractedValue);
                        }
                    }
                });
                if (compiledNode.tagName.toLowerCase() === 't') {
                    const span = document.createElement('span');
                    Array.from(compiledNode.attributes).forEach(attr => {
                        span.setAttribute(attr.name, attr.value);
                    });
                    while (compiledNode.firstChild) {
                        span.appendChild(compiledNode.firstChild);
                    }
                    compiledNode = span;
                }
                if (!ownsOwnClick) {
                    compiledNode.setAttribute("t-on-click", `(el)=>__comp__.handleSelectField?.(el)`);
                }
            }
        }
        return compiledNode;
    }


    /**
     * Compile the root form element.
     * Handles sheets, avatars, chatter, and node aggregation.
     * @param {Element} el - The form element.
     * @param {Record<string, any>} params - Compilation parameters.
     * @returns {Element} - Compiled form.
     */
    compileForm(el, params) {
        this.formView = el
        // localStorage.setItem('elouterHTML',this.formView.outerHTML)
        const sheetNode = el.querySelector("sheet");
        const displayClasses = sheetNode
            ? `d-flex {{ __comp__.uiService.size < ${SIZES.XXL} ? "flex-column" : "flex-nowrap h-100" }}`
            : "d-block";
        const stateClasses =
            "{{ __comp__.props.record.dirty ? 'o_form_dirty' : !__comp__.props.record.isNew ? 'o_form_saved' : '' }}";
        const form = createElement("div", {
            class: "o_form_renderer",
            "t-att-class": "__comp__.props.class",
            "t-attf-class": `{{__comp__.props.record.isInEdition ? 'o_form_editable' : 'o_form_readonly'}} ${displayClasses} ${stateClasses}`,
            "cy-xpath": el.getAttribute("cy-xpath"),
        });
        if (!sheetNode) {
            for (const child of el.childNodes) {
                // ButtonBox are already compiled for the control panel and should not
                // be recompiled for the renderer of the view
                if (child.attributes?.name?.value !== "button_box") {
                    append(form, this.compileNode(child, params));
                }
            }
            form.classList.add("o_form_nosheet");
        }
        else {
            var hasChatter = false
            const chatter = createElement('ChatterComponent', {
                viewId: `__comp__.env.config.viewId`,
                model: `__comp__.env.model.config.resModel`,
            });
            let compiledList = [];
            for (const child of el.childNodes) {
                const compiled = this.compileNode(child, params);
                if (getTag(child, true) === "sheet") {
                    append(form, compiled);
                    compiled.prepend(...compiledList);
                    compiledList = [];
                }
                else if (compiled) {
                    if (child.classList?.contains('oe_chatter')) {
                        hasChatter = true
                        const path = child.getAttribute("cy-xpath")
                        chatter.setAttribute('path', toStringExpression(path))
                        chatter.setAttribute('hasChatter', hasChatter)
                        compiledList.push(chatter)
                    } else {
                        compiledList.push(compiled);
                    }
                    compiledList.push(compiled);
                }
            }
            const preview = el.querySelector('.o_attachment_preview')
            if (preview) {
                chatter.setAttribute('preview', true)
                compiledList.push(chatter)
            }
            if (!hasChatter) {
                chatter.setAttribute('hasChatter', hasChatter)
                compiledList.push(chatter)
            }

            append(form, compiledList);
        }
        return form;
    }

    /**
     * Compile a header element (status bar).
     * Adds buttons, fields, and optional status bar injection.
     * @param {Element} el - Header element.
     * @param {Record<string, any>} params - Compilation parameters.
     * @returns {Element} - Compiled header.
     */
    compileHeader(el, params) {
        const statusBar = createElement("div");
        statusBar.className =
            "o_form_statusbar position-relative d-flex justify-content-between mb-0 mb-md-2 pb-2 pb-md-0";
        statusBar.setAttribute("cy-xpath", el.getAttribute('cy-xpath'));
        statusBar.setAttribute("studio-header", el.getAttribute('studio-header') || "");
        const buttons = [];
        const others = [];
        const hasStatusBar = el.getAttribute('status-bar') || false
        for (const child of el.childNodes) {
            const compiled = this.compileNode(child, params);
            if (!compiled || isTextNode(compiled)) {
                continue;
            }
            if (getTag(child, true) === "field") {
                compiled.setAttribute("showTooltip", true);
                others.push(compiled);
            } else {
                if (compiled.tagName === "ViewButton") {
                    compiled.setAttribute("defaultRank", "'btn-secondary'");
                }
                buttons.push({
                    node: compiled,
                    invisible: getModifier(child, "invisible"),
                });
            }
        }
        if (!hasStatusBar) {
            const addStatusBar = createElement('StatusBar', {
                fields: `__comp__.props.record.fields`,
                viewId: `__comp__.env?.config.viewId`,
                model: `__comp__.env?.model.config.resModel`,
            })
            const path = el.getAttribute("cy-xpath")
            // @fixme: Error occurs when studio reloads (sometimes). Don't remove the below console statement; need to debug.
            addStatusBar.setAttribute("path", toStringExpression(path))
            addStatusBar.setAttribute("header", toStringExpression(el.getAttribute('studio-header') || ""))
            others.push(addStatusBar);
        }
        let slotId = 0;
        const statusBarButtons = createElement("StatusBarButtons");
        const buttonLimit = el.getAttribute("button_limit");
        if (buttonLimit) {
            statusBarButtons.setAttribute("buttonLimit", buttonLimit);
        }
        const invisibleSession = sessionStorage.getItem('invisible');
        const getVisibleExpression = (buttonInfo) => {
            const invisible = buttonInfo.invisible;
            if (invisibleSession) {
                return true;
            }
            if (!invisible || invisible === "False" || invisible === "0") {
                return true;
            }
            if (invisible === "True" || invisible === "1") {
                return false;
            }
            return `!__comp__.evaluateBooleanExpr(${JSON.stringify(
                invisible
            )}, __comp__.props.record.evalContextWithVirtualIds)`;
        };
        for (const buttonInfo of buttons) {
            const button = buttonInfo.node;
            const slot = createElement("t", {
                "t-set-slot": `button_${slotId++}`,
                isVisible: button.getAttribute("t-if") || getVisibleExpression(buttonInfo),
            });
            append(slot, button);
            append(statusBarButtons, slot);
        }
        append(statusBar, statusBarButtons);
        append(statusBar, others);
        return statusBar;
    }

    /**
 * Compile a group element, including inner and outer groups.
 * Handles labels, colspan, slots, and visibility.
 * @param {Element} el - Group element.
 * @param {Record<string, any>} params - Compilation parameters.
 * @returns {Element} - Compiled group.
 */

    compileGroup(el, params) {
        const isOuterGroup = [...el.children].some((c) => getTag(c, true) === "group");
        const formGroup = createElement(isOuterGroup ? "OuterGroup" : "InnerGroup");
        let slotId = 0;
        let sequence = 0;

        if (el.hasAttribute("col")) {
            formGroup.setAttribute("maxCols", el.getAttribute("col"));
        }

        if (el.hasAttribute("string")) {
            const titleSlot = createElement("t", { "t-set-slot": "title" }, [
                makeSeparator(el.getAttribute("string")),
            ]);
            append(formGroup, titleSlot);
        }

        let forceNewline = false;

        for (const child of el.children) {
            if (getTag(child, true) === "newline") {
                forceNewline = true;
                continue;
            }

            const invisible = getModifier(child, "invisible");

            const mainSlot = createElement("t", {
                "t-set-slot": `item_${slotId++}`,
                type: "'item'",
                sequence: sequence++,
                "t-slot-scope": "scope",
            });
            let itemSpan = parseInt(child.getAttribute("colspan") || "1", 10);

            if (forceNewline) {
                mainSlot.setAttribute("newline", true);
                forceNewline = false;
            }

            if (getTag(child, true) === "separator") {
                itemSpan = parseInt(formGroup.getAttribute("maxCols") || 2, 10);
            }

            if (child.matches("div[class='clearfix']:empty")) {
                itemSpan = parseInt(formGroup.getAttribute("maxCols") || 2, 10);
            }

            let slotContent;
            if (getTag(child, true) === "field") {
                const addLabel = child.hasAttribute("nolabel")
                    ? child.getAttribute("nolabel") !== "1"
                    : true;
                const invisible_session = sessionStorage.getItem('invisible');
                slotContent = this.compileNode(child, { ...params, currentSlot: mainSlot }, !!invisible_session);
                if (slotContent && addLabel && !isOuterGroup && !isTextNode(slotContent)) {
                    itemSpan = itemSpan === 1 ? itemSpan + 1 : itemSpan;
                    const fieldName = child.getAttribute("name");
                    const fieldId = slotContent.getAttribute("id") || fieldName;
                    const props = {
                        id: `${fieldId}`,
                        fieldName: `'${fieldName}'`,
                        record: `__comp__.props.record`,
                        string: child.hasAttribute("string")
                            ? toStringExpression(child.getAttribute("string"))
                            : `__comp__.props.record.fields.${fieldName}.string`,
                        fieldInfo: `__comp__.props.archInfo.fieldNodes[${fieldId}]`,
                    };
                    mainSlot.setAttribute("props", objectToString(props));
                    mainSlot.setAttribute("Component", "__comp__.constructor.components.FormLabel");
                    mainSlot.setAttribute("subType", "'item_component'");
                    mainSlot.setAttribute("cy-xpath", `'${child.getAttribute("cy-xpath")}'`);
                } else {
                }
            } else {
                if (getTag(child, true) === "div" && child.children[0]) {

                    for (const element of child.children) {
                        if (getTag(element, true) === "span") {
                            const spanInvisible = toStringExpression(element.getAttribute('invisible') || '0')
                            element.setAttribute("t-on-click", `(ev)=>__comp__.onSpanClick(ev, ${spanInvisible})`)
                            element.setAttribute("t-att-class", `__comp__.evaluateBooleanExpr(${JSON.stringify(
                                getModifier(element, "invisible")
                            )},__comp__.props.record.evalContextWithVirtualIds)
                                                                    ? 'cy-studio-striped' : ''`)
                        }
                    }

                    mainSlot.setAttribute("cy-xpath", `'${child.children[0].getAttribute("cy-xpath")}'`);
                }
                // TODO: When every apps will be revamp, we could remove the condition using 'o_td_label' in favor of 'o_wrap_label'
                if (
                    child.classList.contains("o_wrap_label") ||
                    child.classList.contains("o_td_label") ||
                    getTag(child, true) === "label"
                ) {
                    if (child.hasAttribute("striped")) {
                        mainSlot.setAttribute("striped", "'cy-studio-striped'")
                    }
                    mainSlot.setAttribute("subType", "'label'");
                    child.classList.remove("o_wrap_label");
                    mainSlot.setAttribute("cy-xpath", `'${child.getAttribute("cy-xpath")}'`);
                }
                slotContent = this.compileNode(child, { ...params, currentSlot: mainSlot }, false);
            }

            if (slotContent && !isTextNode(slotContent)) {
                let isVisibleExpr;
                if (!invisible || invisible === "False" || invisible === "0") {
                    isVisibleExpr = "true";
                } else if (invisible === "True" || invisible === "1") {
                    isVisibleExpr = "false";
                } else {
                    isVisibleExpr = `!__comp__.evaluateBooleanExpr(${JSON.stringify(
                        invisible
                    )},__comp__.props.record.evalContextWithVirtualIds)`;
                }
                //                    const invisible_session =  sessionStorage.getItem('invisible');
                //                    if(invisible_session){
                mainSlot.setAttribute("invisibleStriped", `!${isVisibleExpr}`)
                mainSlot.setAttribute("isVisible", true);
                //                    }else{
                //                        mainSlot.setAttribute("isVisible", isVisibleExpr);
                //                    }

                if (itemSpan > 0) {
                    mainSlot.setAttribute("itemSpan", `${itemSpan}`);
                }

                const groupClassExpr = `scope && scope.className`;
                if (isComponentNode(slotContent)) {
                    if (getTag(slotContent) === "FormLabel") {
                        mainSlot.prepend(
                            createElement("t", {
                                "t-set": "addClass",
                                "t-value": groupClassExpr,
                            })
                        );
                        combineAttributes(
                            slotContent,
                            "className",
                            `(addClass ? " " + addClass : "")`,
                            `+`
                        );
                    } else if (getTag(child, true) !== "button") {
                        if (slotContent.hasAttribute("class")) {
                            mainSlot.prepend(
                                createElement("t", {
                                    "t-set": "addClass",
                                    "t-value": groupClassExpr,
                                })
                            );
                            combineAttributes(
                                slotContent,
                                "class",
                                `(addClass ? " " + addClass : "")`,
                                `+`
                            );
                        } else {
                            slotContent.setAttribute("class", groupClassExpr);
                        }
                    }
                } else {
                    appendAttf(slotContent, "class", `${groupClassExpr} || ""`);
                }
                append(mainSlot, slotContent);
                append(formGroup, mainSlot);
            }
        }
        var GroupPath = el.getAttribute('cy-xpath')
        formGroup.setAttribute("cy-xpath", `'${GroupPath}'`);

        return formGroup;
    }


    /**
    * Generate a FormLabel component for a field.
    * @param {string} fieldId - Field ID.
    * @param {string} fieldName - Field name.
    * @param {string} fieldString - Field string.
    * @param {Element} label - Original label element.
    * @param {Record<string, any>} params - Additional parameters.
    * @returns {Element} - Compiled FormLabel element.
    */
    createLabelFromField(fieldId, fieldName, fieldString, label, params) {
        let labelText = label.textContent || fieldString;
        let cyXpath = ''
        if (label.hasAttribute("cyXpath")) {
            cyXpath = toStringExpression(label.getAttribute("cyXpath"))
        }

        if (label.hasAttribute("data-no-label")) {
            labelText = toStringExpression("");
        } else {
            labelText = labelText
                ? toStringExpression(labelText)
                : `__comp__.props.record.fields['${fieldName}'].string`;
        }
        const formLabel = createElement("FormLabel", {
            id: `'${fieldId}'`,
            fieldName: `'${fieldName}'`,
            record: `__comp__.props.record`,
            fieldInfo: `__comp__.props.archInfo.fieldNodes['${fieldId}']`,
            className: `"${label.className}"`,
            string: labelText,
            cyXpath: cyXpath,
        });
        const condition = label.getAttribute("t-if");
        if (condition) {
            formLabel.setAttribute("t-if", condition);
        }
        return formLabel;
    }

    /**
    * @param {Element} el
    * @param {Record<string, any>} params
    * @returns {Element}
    */
    compileLabel(el, params) {
        const forAttr = el.getAttribute("for");
        // A label can contain or not the labelable Element it is referring to.
        // If it doesn't, there is no `for=`
        // Otherwise, the targetted element is somewhere else among its nextChildren
        if (forAttr) {
            let label = createElement("label");
            copyAttributes(el, label);
            const string = el.getAttribute("string");
            if (string) {
                append(label, createTextNode(string));
            } else if (string === "") {
                label.setAttribute("data-no-label", "true");
            }
            if (getTag(label, true) === "label") {
                label.setAttribute("cyXpath", el.getAttribute("cy-xpath") || '');
            }
            if (this.encounteredFields[forAttr]) {
                label = this.encounteredFields[forAttr](label);
            } else {
                this.pushLabel(forAttr, label);
            }

            return label;
        }
        const res = this.compileGenericNode(el, params);
        copyAttributes(el, res);
        return res;
    }


    /**
    * Compile a notebook element and its pages.
    * Supports invisible pages, anchors, and default page selection.
    * @param {Element} el - Notebook element.
    * @param {Record<string, any>} params - Compilation parameters.
    * @returns {Element} - Compiled notebook.
    */
    compileNotebook(el, params) {
        const invisible_session = sessionStorage.getItem('invisible');
        const noteBookId = this.noteBookId++;
        const noteBook = createElement("Notebook");
        const pageAnchors = [...document.querySelectorAll("[href^=\\#]")]
            .map((a) => CSS.escape(a.getAttribute("href").substring(1)))
            .filter((a) => a.length);
        const noteBookAnchors = {};

        if (el.hasAttribute("class")) {
            noteBook.setAttribute("className", toStringExpression(el.getAttribute("class")));
            el.removeAttribute("class");
        }

        noteBook.setAttribute(
            "defaultPage",
            `__comp__.props.record.isNew ? undefined : __comp__.props.activeNotebookPages[${noteBookId}]`
        );
        noteBook.setAttribute(
            "onPageUpdate",
            `(page) => __comp__.props.onNotebookPageChange(${noteBookId}, page)`
        );
        noteBook.setAttribute('cyXpath', toStringExpression(el.getAttribute("cy-xpath") || ""))
        for (const child of el.children) {
            if (getTag(child, true) !== "page") {
                continue;
            }
            const invisible = getModifier(child, "invisible");

            const pageSlot = createElement("t");
            append(noteBook, pageSlot);

            const pageId = `page_${this.id++}`;
            const pageTitle = toStringExpression(
                child.getAttribute("string") || child.getAttribute("name") || ""
            );
            const pageNodeName = toStringExpression(child.getAttribute("name") || "");

            pageSlot.setAttribute("t-set-slot", pageId);
            pageSlot.setAttribute("title", pageTitle);
            pageSlot.setAttribute("name", pageNodeName);
            pageSlot.setAttribute("cyXpath", toStringExpression(child.getAttribute("cy-xpath") || ""));
            pageSlot.setAttribute("groups", toStringExpression(child.getAttribute("groups") || ""));
            pageSlot.setAttribute("autofocus", toStringExpression(child.getAttribute("autofocus") || ""));
            pageSlot.setAttribute("invisible", toStringExpression(invisible || "False"));

            if (child.hasAttribute("striped")) {
                child.classList.add('cy-studio-striped')
            }

            if (child.className) {
                pageSlot.setAttribute("className", `"${child.className}"`);
            }

            if (child.getAttribute("autofocus") === "autofocus") {
                noteBook.setAttribute(
                    "defaultPage",
                    `__comp__.props.record.isNew ? "${pageId}" : (__comp__.props.activeNotebookPages[${noteBookId}] || "${pageId}")`
                );
            }

            for (const anchor of child.querySelectorAll("[href^=\\#]")) {
                const anchorValue = CSS.escape(anchor.getAttribute("href").substring(1));
                if (!anchorValue.length) {
                    continue;
                }
                pageAnchors.push(anchorValue);
                noteBookAnchors[anchorValue] = {
                    origin: `'${pageId}'`,
                };
            }

            let isVisibleExpr;
            if (!invisible || invisible === "False" || invisible === "0") {
                isVisibleExpr = "true";
            } else if (invisible === "True" || invisible === "1") {
                isVisibleExpr = "false";
            } else {
                isVisibleExpr = `!__comp__.evaluateBooleanExpr(${JSON.stringify(
                    invisible
                )},__comp__.props.record.evalContextWithVirtualIds)`;
            }
            //            if(invisible_session){
            pageSlot.setAttribute("isVisible", true);
            pageSlot.setAttribute("invisibleStriped", `!${isVisibleExpr}`)

            for (const contents of child.children) {
                append(pageSlot, this.compileNode(contents, { ...params, currentSlot: pageSlot }));
            }
        }

        if (pageAnchors.length) {
            // If anchors from the page are targetting an element
            // present in the notebook, it must be aware of the
            // page that contains the corresponding element
            for (const anchor of pageAnchors) {
                let pageId = 1;
                for (const child of el.children) {
                    if (child.querySelector(`#${anchor}`)) {
                        noteBookAnchors[anchor].target = `'page_${pageId}'`;
                        noteBookAnchors[anchor] = objectToString(noteBookAnchors[anchor]);
                        break;
                    }
                    pageId++;
                }
            }
            noteBook.setAttribute("anchors", objectToString(noteBookAnchors));
        }

        return noteBook;
    }

    /**
    * @param {Element} el
    * @param {Record<string, any>} params
    * @returns {Element}
    */
    compileButtonBox(el, params) {
        if (!el.children.length) {
            return this.compileGenericNode(el, params);
        }

        el.classList.remove("oe_button_box");
        const buttonBox = createElement("ButtonBox");
        buttonBox.setAttribute("t-if", "!__comp__.env.inDialog");
        buttonBox.setAttribute("cyXpath", toStringExpression(el.getAttribute("cy-xpath") || ""))
        let slotId = 0;
        let hasContent = false;
        for (const child of el.children) {
            const invisible = getModifier(child, "invisible");
            //            if (!params.compileInvisibleNodes && (invisible === "True" || invisible === "1")) {
            //                continue;
            //            }
            hasContent = true;
            let isVisibleExpr;
            if (!invisible || invisible === "False" || invisible === "0") {
                isVisibleExpr = "true";
            } else if (invisible === "True" || invisible === "1") {
                isVisibleExpr = "false";
            } else {
                isVisibleExpr = `!__comp__.evaluateBooleanExpr(${JSON.stringify(
                    invisible
                )},__comp__.props.record.evalContextWithVirtualIds)`;
            }
            //            let mainSlot = ""
            //            const invisible_session =  sessionStorage.getItem('invisible');
            //              mainSlot = createElement("t", {
            //            "t-set-slot": `slot_${slotId++}`,isVisible: invisible_session ? true : isVisibleExpr,
            //            });
            let mainSlot = createElement("t", {
                "t-set-slot": `slot_${slotId++}`,
                isVisible: "true",
            });
            if (child.getAttribute('string')) {
                child.setAttribute('string', child.getAttribute('string') || "")
                child.setAttribute('stringPath', child.querySelector('.o_stat_text')?.getAttribute('cy-xpath') || child.getAttribute('cy-xpath') || "")
            } else if (child.firstElementChild?.tagName === 'field') {
                child.setAttribute('string', child.firstElementChild.getAttribute('string') || "")
                child.setAttribute('stringPath', child.firstElementChild.getAttribute('cy-xpath') || "")
                child.setAttribute('StatusLabelPath', child.querySelector('[status_label]')?.getAttribute('cy-xpath') || false)
            } else {
                child.setAttribute('string', child.querySelector('.o_stat_text')?.textContent.trim() || "")
                child.setAttribute('stringPath', child.querySelector('.o_stat_text')?.getAttribute('cy-xpath') || "")
            }


            if (child.tagName === "button" || child.children.tagName === "button") {
                child.classList.add(
                    "oe_stat_button",
                    "btn",
                    "btn-outline-secondary",
                    "flex-grow-1",
                    "flex-lg-grow-0"
                );
            }
            if (child.tagName === "field") {
                child.classList.add("d-inline-block", "mb-0", "z-index-0");
            }
            //            if (invisible_session ){
            //                const compileNode = this.compileNode(child, params, false)
            //                compileNode.setAttribute('striped', `!${isVisibleExpr}`)
            //                append(mainSlot, compileNode);
            //            } else {
            //                append(mainSlot, this.compileNode(child, params, false));
            //            }
            const compiledButton = this.compileNode(child, params, true);
            if (invisible === "True" || invisible === "1") {
                compiledButton.setAttribute("striped", "true");
            }
            append(mainSlot, compiledButton);
            append(buttonBox, mainSlot);
        }

        return hasContent ? buttonBox : "";
    }

    /**
     * Compile a sheet element (form sheet background and foreground).
     * Handles avatars, ribbons, badges, and children nodes.
     * @param {Element} el - Sheet element.
     * @param {Record<string, any>} params - Compilation parameters.
     * @returns {Element} - Compiled sheet element.
     */
    compileSheet(el, params) {
        const sheetBG = createElement("div");
        sheetBG.className = "o_form_sheet_bg";

        const sheetFG = createElement("div");
        sheetFG.className = "o_form_sheet position-relative";
        sheetFG.setAttribute("cy-xpath", el.getAttribute("cy-xpath"));
        const newSheet = el.getAttribute("sheet");
        if (newSheet) {
            sheetFG.setAttribute("sheet", newSheet);
        }
        append(sheetBG, sheetFG);
        var title_count = 0
        var badge_count = 0
        var ribbon_count = 0
        var avatar_count = 0
        for (const child of el.childNodes) {
            if (getTag(child, true) == "widget") {
                ribbon_count++;
            }
            if (getTag(child, true) === "div") {
                if (child.className.includes('oe_title')) {
                    title_count++;
                }
                if (child.className.includes('badge')) {
                    badge_count++;
                }
            }
            if (getTag(child, true) === "field") {
                if (child.className.includes('oe_avatar')) {
                    avatar_count++
                }
            }
        }
        for (const child of el.childNodes) {
            const compiled = this.compileNode(child, params);
            let hasAvatar = el.getAttribute('avatar') || false
            if (!badge_count && !ribbon_count && !avatar_count && !hasAvatar) {

                var path = child.nextElementSibling?.children[0]?.classList.contains('button-box-container') ? child.parentElement.firstElementChild.nextElementSibling?.getAttribute("cy-xpath") : child.nextElementSibling?.getAttribute("cy-xpath")
                if (!path) {
                    if (child.nodeType === 1) {
                        path = child.previousElementSibling?.children[0]?.classList.contains('button-box-container') ? child.previousElementSibling.parentElement.firstElementChild.nextElementSibling?.getAttribute("cy-xpath") : child.previousElementSibling?.getAttribute("cy-xpath")
                    }
                }
                if (path) {
                    const Avatar = createElement('AvatarComponent', {
                        fields: `__comp__.props.record.fields`,
                        viewId: `__comp__.env.config.viewId`,
                        model: `__comp__.env.model.config.resModel`,
                    });
                    Avatar.setAttribute("path", toStringExpression(path))
                    avatar_count = 1
                    append(sheetFG, Avatar)
                }


            }
            if (!compiled) {
                continue;
            }
            if (compiled.nodeName === "ButtonBox") {
                // in form views with a sheet, the button box is moved to the
                // control panel, and in dialogs, there's no button box
                continue;
            }
            if (getTag(child, true) === "field") {
                compiled.setAttribute("showTooltip", true);
            }
            if (getTag(child, true) == "widget") {
                ribbon_count--;
            }
            if (getTag(child, true) === "div") {

                if (child.className.includes('oe_title')) {
                    title_count--;
                }
                if (child.className.includes('badge')) {
                    badge_count--;
                }
            }
            append(sheetFG, compiled);

        }
        return sheetBG;
    }
    /**
     * Compile a button element.
     * @param {Element} el - Button element.
     * @param {Record<string, any>} params - Compilation parameters.
     * @returns {Element} - Compiled button element.
     */
    compileButton(el, params) {
        return super.compileButton(el, params)
    }
}