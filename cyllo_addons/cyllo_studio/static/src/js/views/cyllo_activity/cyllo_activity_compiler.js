/* @odoo-module */

/**
 * Custom ActivityCompiler to handle additional click behavior and custom styling
 * for fields in Odoo Studio activity records.
 */
import { createElement, extractAttributes } from "@web/core/utils/xml";
import { toInterpolatedStringExpression, ViewCompiler } from "@web/views/view_compiler";
import { toStringExpression } from "@web/views/utils";
import { ActivityCompiler } from "@mail/views/web/activity/activity_compiler";

export class CylloActivityCompiler extends ActivityCompiler {
    /**
     * Compile a field element, optionally attaching click handlers and classes.
     */
    compileField(el, params) {
        let compiled;
        if (el.hasAttribute("widget")) {
            compiled = super.compileField(el, params);
            compiled.setAttribute(
                "t-on-click",
                `(el)=>__comp__.handleFieldWidgetClick(el,"${el.getAttribute("name")}",
                "${el.getAttribute("cy-xpath")}")`
            );
        } else {
            // fields without a specified widget are rendered as simple spans in activity records
              const attributes = {
                bold: el.getAttribute("bold")?.toLowerCase() === "true" ? true : false,
                display: el.getAttribute("display") ,
                muted: el.getAttribute("muted")?.toLowerCase() === "true" ? true : false
            };
            const attributesString = JSON.stringify(attributes);
            const fieldName = el.getAttribute("name");
            compiled = createElement("div", {
                "t-out": `record["${el.getAttribute("name")}"].value`,
                "cy-xpath": el.getAttribute("cy-xpath"),
                "t-on-click": `(el)=>__comp__.handleFieldClick(${attributesString}, "${fieldName}", "${el.getAttribute("cy-xpath")}")`,
            });
        }
        const classNames = [];
        if (el.getAttribute("display") === "right") {
            classNames.push("float-end")
        }
        if (el.getAttribute("display") === "full") {
            classNames.push("d-block", "text-truncate");
        } else {
            classNames.push("d-inline-block");
        }
        if (el.getAttribute("bold")) {
            if (el.getAttribute("bold") === 'False') {
                const boldIndex = classNames.indexOf("fw-bold");
                if (boldIndex > -1) {
                    classNames.splice(boldIndex, 1);
                }
            } else {
                if (!classNames.includes("fw-bold")) {
                    classNames.push("fw-bold");
                }
            }
        }

    if (el.getAttribute("muted")) {
        if (el.getAttribute("muted") === 'False') {
            const mutedIndex = classNames.indexOf("text-muted");
            if (mutedIndex > -1) {
                classNames.splice(mutedIndex, 1);
            }
        } else {
            if (!classNames.includes("text-muted")) {
                classNames.push("text-muted");
            }
        }
    }
        if (classNames.length > 0) {
            const clsFormatted = el.hasAttribute("widget")
                ? toStringExpression(classNames.join(" "))
                : classNames.join(" ");
            compiled.setAttribute("class", clsFormatted);
        }

        const attrs = {};
        for (const attr of el.attributes) {
            attrs[attr.name] = attr.value;
        }

        if (el.hasAttribute("widget")) {
            const attrsParts = Object.entries(attrs).map(([key, value]) => {
                if (key.startsWith("t-attf-")) {
                    key = key.slice(7);
                    value = toInterpolatedStringExpression(value);
                } else if (key.startsWith("t-att-")) {
                    key = key.slice(6);
                    value = `"" + (${value})`;
                } else if (key.startsWith("t-att")) {
                    throw new Error("t-att on <field> nodes is not supported");
                } else if (!key.startsWith("t-")) {
                    value = toStringExpression(value);
                }
                return `'${key}':${value}`;
            });
            compiled.setAttribute("attrs", `{${attrsParts.join(",")}}`);
        }

        for (const attr in attrs) {
            if (attr.startsWith("t-") && !attr.startsWith("t-att")) {
                compiled.setAttribute(attr, attrs[attr]);
            }
        }

        if (el.hasAttribute("widget")) {
            // Widget fields compile to a <Field/> component invocation, which has
            // no plain cy-xpath DOM attribute for the selected-field highlight to
            // target. Wrap it in a transparent span that carries one.
            compiled = createElement("span", { "cy-xpath": el.getAttribute("cy-xpath") }, [compiled]);
        }

        return compiled;
    }
}

CylloActivityCompiler.OWL_DIRECTIVE_WHITELIST = [
    ...ActivityCompiler.OWL_DIRECTIVE_WHITELIST,
];