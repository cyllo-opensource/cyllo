/** @odoo-module **/

import SurveyFormWidget from "@survey/js/survey_form";

SurveyFormWidget.include({
    start: function () {
        return this._super(...arguments).then(() => this._moveTopBarIntoWrap());
    },

    /**
     * Place the progress bar at the top of the survey area, below any banners.
     */
    _moveTopBarIntoWrap: function () {
        const topBar = document.querySelector('.o_survey_top_bar');
        const wrap = this.el.closest('.o_survey_wrap');
        if (topBar && wrap) {
            wrap.prepend(topBar);
        }
    },
});
