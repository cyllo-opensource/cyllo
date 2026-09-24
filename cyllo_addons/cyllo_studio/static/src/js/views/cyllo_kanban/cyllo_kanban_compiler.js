/** @odoo-module **/
/**
 * CylloKanbanCompiler
 *
 * Extends Odoo's KanbanCompiler to provide custom compilation logic
 * for Cyllo Studio Kanban views.
 *
 * Key Features:
 * - Adds click handlers for ribbon, field, and span elements.
 * - Handles conditional visibility using "invisible" attribute and session flags.
 * - Preserves original attributes like 'cy-xpath', 'name', and 'field-tag'.
 * - Enhances field, node, Kanban card, and generic node compilation.
 */
import {
    append,
    combineAttributes,
    createElement,
    extractAttributes,
    getTag,
} from "@web/core/utils/xml";
import {
    toStringExpression
} from "@web/views/utils";
import {
    toInterpolatedStringExpression,
    ViewCompiler
} from "@web/views/view_compiler";
import {
    KanbanCompiler
} from "@web/views/kanban/kanban_compiler";
import {
    patch
} from "@web/core/utils/patch";
import {
    getModifier,
    isComponentNode,
    isTextNode,
} from "@web/views/view_compiler";


export class CylloKanbanCompiler extends KanbanCompiler {
    setup() {
        super.setup();
        this.isKanbanView = true;
    }

    /**
     * Compile a field element in the Kanban view.
     *
     * Adds custom attributes, click handlers, and handles visibility.
     *
     * @param {Element} el - The DOM element representing the field.
     * @param {Object} params - Additional compilation parameters.
     * @returns {Element} - The compiled field element.
     */
    compileField(el, params) {
        const compiled = super.compileField(el, params);
        if (!el.hasAttribute("widget")) {
            const path = el.getAttribute('cy-xpath')
            const name = el.getAttribute('name')
            compiled.setAttribute('cy-xpath', path)
            compiled.setAttribute('name', name)
            compiled.setAttribute('field-tag', true)
            compiled.setAttribute("t-on-click.self", `(el)=>__comp__.handleSelectField(el)`)
        }
        const invisible = getModifier(el, "invisible");
        const invisible_session = sessionStorage.getItem('invisible');

        if (invisible_session && invisible && invisible !== "False" && invisible !== "0") {
            let isVisibleExpr;
            if (invisible === "True" || invisible === "1" || invisible) {
                isVisibleExpr = "false";
            } else {
                isVisibleExpr = `!__comp__.evaluateBooleanExpr(${JSON.stringify(
                    invisible
                )}, __comp__.props.record.evalContextWithVirtualIds)`;
            }
            compiled.setAttribute('striped', `!${isVisibleExpr}`)
            compiled.setAttribute('invisible', `${invisible}`)
        }

        return compiled
    }

    /**
     * Compile a generic node in the Kanban view.
     *
     * Adds click handlers, manages visibility, and adjusts classes for striped styling.
     *
     * @param {Node} node - The DOM node to compile.
     * @param {Object} params - Compilation parameters.
     * @param {boolean} evalInvisible - Whether to evaluate "invisible" modifiers.
     * @returns {Node} - The compiled node.
     */
    compileNode(node, params = {}, evalInvisible = true) {
        const invisible_session = sessionStorage.getItem('invisible');
        if (invisible_session) {
            evalInvisible = false;
        }
        let compiledNode = super.compileNode(node, params, evalInvisible);
        if (!compiledNode) {
            return compiledNode;
        }
        if (node.nodeType === 1 && node.classList?.contains("ribbon")) {
            compiledNode.setAttribute(
                "t-on-click",
                `(ev)=>__comp__.handleRibbonClick(ev)`
            );

            compiledNode.style = (compiledNode.getAttribute("style") || "") + "cursor:pointer;";
            const isSelected = node.getAttribute('data-selected');
            const selectedXPath = sessionStorage.getItem('SelectedRibbonXPath');
            const thisXPath = node.getAttribute('cy-xpath');
            if (selectedXPath && thisXPath) {
                // If session has a selected ribbon, show only that one regardless of data-selected
                if (selectedXPath === thisXPath) {
                    compiledNode.style = (compiledNode.getAttribute("style") || "").replace('display:none;', '');
                } else {
                    compiledNode.style = (compiledNode.getAttribute("style") || "") + "display:none;";
                }
            } else if (isSelected !== '1') {
                compiledNode.style = (compiledNode.getAttribute("style") || "") + "display:none;";
            }
        }
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
        }
        const validAttributes = ["t-out", "t-esc"];
        if (compiledNode?.attributes) {
            const AttrArray = Array.from(compiledNode.attributes);
            const hasValidAttribute = validAttributes.some(attr =>
                AttrArray.some(nodeAttr => nodeAttr.name === attr)
            );
            if (node.tagName.toLowerCase() === 'span' && !compiledNode.children.length > 0) {
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
                compiledNode.setAttribute("t-on-click", `(el)=>__comp__.handleSelectField(el)`);
                if (node?.tagName?.toLowerCase() === "a") {
                    const fragment = document.createDocumentFragment();
                    while (compiledNode.firstChild) {
                        fragment.appendChild(compiledNode.firstChild);
                    }
                    // replace with the first child (span in your case)
                    compiledNode = fragment.firstChild;
                }
            }
            if (node.nodeType === 1 && node.tagName.toLowerCase() === "img") {
                const srcAttr = node.getAttribute("t-att-src");
                let fieldName = null
                if (srcAttr && srcAttr.includes("kanban_image")) {
                    // Extract the second argument inside kanban_image('model', 'field', ...)
                    const match = srcAttr.match(/kanban_image\([^,]+,\s*'([^']+)'/);
                    if (match) {
                        fieldName = match[1];
                    }
                }
                // fallback (if no t-att-src, try src query param)
                if (!fieldName) {
                    const src = node.getAttribute("src") || "";
                    const paramMatch = src.match(/field=([^&]+)/);
                    if (paramMatch) {
                        fieldName = paramMatch[1];
                    }
                }
                if (fieldName) {
                    compiledNode.setAttribute("name", fieldName);
                    compiledNode.setAttribute("field-tag", true);
                    compiledNode.setAttribute(
                        "t-on-click",
                        `(ev)=>__comp__.handleSelectField(ev)`
                    );
                    compiledNode.style =
                        (compiledNode.getAttribute("style") || "") + "cursor:pointer;";
                }
            }

        }
        return compiledNode;
    }
    /**
     * Compile a Kanban card element.
     *
     * Adds striped visibility handling for cards based on the invisible modifier.
     *
     * @param {Element} el - The DOM element representing the Kanban card.
     * @param {Object} params - Compilation parameters.
     * @returns {Element} - The compiled Kanban card element.
     */
    compileKanbanCard(el, params) {
        const compiled = super.compileKanbanCard(el, params);

        const invisible_session = sessionStorage.getItem('invisible');
        if (invisible_session) {
            const invisible = getModifier(el, "invisible");

            if (invisible && invisible !== "False" && invisible !== "0") {
                let isVisibleExpr;
                if (invisible === "True" || invisible === "1") {
                    isVisibleExpr = "false";
                } else {
                    isVisibleExpr = `!__comp__.evaluateBooleanExpr(${JSON.stringify(
                        invisible
                    )}, __comp__.props.record.evalContextWithVirtualIds)`;
                }

                compiled.setAttribute('invisibleStriped', `!${isVisibleExpr}`)
                compiled.setAttribute('isVisible', true);
            }
        }

        return compiled;
    }

    /**
     * Compile a generic node element in the Kanban view.
     *
     * Handles striped visibility and applies proper CSS classes.
     *
     * @param {Element} el - The DOM element to compile.
     * @param {Object} params - Compilation parameters.
     * @returns {Element} - The compiled element.
     */
    compileGenericNode(el, params) {
        const compiled = super.compileGenericNode(el, params);

        const invisible_session = sessionStorage.getItem('invisible');
        if (invisible_session && el.nodeType === 1) {
            const invisible = getModifier(el, "invisible");

            if (invisible && invisible !== "False" && invisible !== "0") {
                let isVisibleExpr;
                if (invisible === "True" || invisible === "1") {
                    isVisibleExpr = "false";
                } else {
                    isVisibleExpr = `!__comp__.evaluateBooleanExpr(${JSON.stringify(
                        invisible
                    )}, __comp__.props.record.evalContextWithVirtualIds)`;
                }

                if (el.hasAttribute("striped")) {
                    compiled.classList.add('cy-studio-striped')
                }

                const currentClass = compiled.getAttribute("t-att-class") || "";
                const stripedClass = `(!${isVisibleExpr}) ? 'cy-studio-striped' : ''`;

                if (currentClass) {
                    compiled.setAttribute("t-att-class", `${currentClass} + ' ' + (${stripedClass})`);
                } else {
                    compiled.setAttribute("t-att-class", stripedClass);
                }
            }
        }

        return compiled;
    }
}

CylloKanbanCompiler.OWL_DIRECTIVE_WHITELIST = [
    ...KanbanCompiler.OWL_DIRECTIVE_WHITELIST,
];
