/** @odoo-module **/

import SurveyFormWidget from "@survey/js/survey_form";

SurveyFormWidget.include({
    /**
     * Ignore clicks on a disabled navigation button: the arrow-left key clicks
     * the previous button even when it is disabled on the finished screen.
     */
    _onSubmit: function (event) {
        if (event.currentTarget.disabled) {
            event.preventDefault();
            return;
        }
        return this._super(...arguments);
    },

    /**
     * Ignore a new submit while the previous one is still running, so a click
     * on the navigation arrows during a slow page or finish cannot resubmit an
     * answer the server has already completed.
     */
    _submitForm: async function () {
        if (this.isSubmitting) {
            return;
        }
        this._setSubmitting(true);
        this.nextScreenPending = false;
        try {
            return await this._super(...arguments);
        } finally {
            if (!this.nextScreenPending) {
                this._setSubmitting(false);
            }
        }
    },

    /**
     * Keep the form locked until the next screen is displayed.
     */
    _nextScreen: async function () {
        this.nextScreenPending = true;
        try {
            return await this._super(...arguments);
        } finally {
            this.nextScreenPending = false;
            this._setSubmitting(false);
        }
    },

    /**
     * Flag the form as submitting and dim the navigation arrows meanwhile.
     */
    _setSubmitting: function (submitting) {
        this.isSubmitting = submitting;
        $('.o_survey_navigation_wrapper').toggleClass('o_survey_navigation_busy', submitting);
    },
});
