/** @odoo-module **/

import { registry } from "@web/core/registry";
import { TourError } from "@web_tour/tour_service/tour_utils";

/**
 * Fail the tour when the generic survey error banner is visible.
 */
function assertNoSurveyError() {
    if (document.querySelector(".o_survey_error:not(.d-none)")) {
        throw new TourError("The survey error banner is shown.");
    }
}

/**
 * Mark the body once ``delay`` ms passed, so the next step waits for any late RPC.
 */
function markAfter(className, delay) {
    setTimeout(() => document.body.classList.add(className), delay);
}

registry.category("web_tour.tours").add("cyllo_survey_navigation_after_finish", {
    test: true,
    steps: () => [
        {
            content: "Start the survey",
            trigger: 'button.btn[value="start"]',
        },
        {
            content: "Answer the question",
            trigger: "div.js_question-wrapper input.o_survey_question_text_box",
            run: "text Alice",
        },
        {
            content: "Click finish twice in a row",
            trigger: '.o_survey_navigation_wrapper button[value="finish"]',
            run: function () {
                const button = this.$anchor[0];
                button.click();
                button.click();
            },
        },
        {
            content: "Wait for the finished screen",
            trigger: ".o_survey_finished",
            run: () => markAfter("o_cy_finish_settled", 1500),
        },
        {
            content: "No error after the double click",
            trigger: "body.o_cy_finish_settled",
            run: assertNoSurveyError,
        },
        {
            content: "Press arrow-left on the finished screen",
            trigger: "body.o_cy_finish_settled .o_survey_finished",
            run: () => {
                if (!document.querySelector('.o_survey_navigation_wrapper button[value="previous"]:disabled')) {
                    throw new TourError("The previous button should be shown disabled.");
                }
                document.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowLeft", bubbles: true }));
                markAfter("o_cy_arrow_settled", 1500);
            },
        },
        {
            content: "No error after arrow-left",
            trigger: "body.o_cy_arrow_settled .o_survey_finished",
            run: assertNoSurveyError,
        },
    ],
});
