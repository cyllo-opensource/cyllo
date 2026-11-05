/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import SurveyFormWidget from "@survey/js/survey_form";

SurveyFormWidget.include({
    events: Object.assign({}, SurveyFormWidget.prototype.events, {
        'change .o_survey_upload_input': '_onUploadInputChange',
    }),

    /**
     * Read the selected file as base64, rejecting it when it exceeds the size limit.
     */
    _onUploadInputChange: function (ev) {
        const input = ev.currentTarget;
        const $input = $(input);
        const $questionWrapper = $input.closest(".js_question-wrapper");
        const file = input.files[0];
        $input.removeData('uploadFile');
        $questionWrapper.find('.o_survey_question_error').empty().removeClass('slide_in');
        if (!file) {
            return;
        }
        const maxSize = parseInt(input.dataset.maxSize);
        if (file.size > maxSize) {
            input.value = '';
            this._showErrors({
                [$questionWrapper.attr('id')]: _t("The file must not exceed %s KB.", Math.floor(maxSize / 1024)),
            });
            return;
        }
        const reader = new FileReader();
        reader.onload = () => {
            $input.data('uploadFile', {
                name: file.name,
                data: reader.result.split(',')[1],
            });
        };
        reader.readAsDataURL(file);
    },

    _validateForm: function ($form, formData) {
        const isValid = this._super(...arguments);
        const errors = {};
        const inactiveQuestionIds = this.options.sessionInProgress ? [] : this._getInactiveConditionalQuestionIds();
        $form.find('[data-question-type="upload"]').each(function () {
            const $questionWrapper = $(this).closest(".js_question-wrapper");
            const questionId = $questionWrapper.attr('id');
            if (inactiveQuestionIds.includes(parseInt(questionId))) {
                return;
            }
            if ($questionWrapper.data('required') && !$(this).data('uploadFile') && !this.dataset.existingFile) {
                errors[questionId] = $questionWrapper.data('constrErrorMsg');
            }
        });
        if (Object.keys(errors).length > 0) {
            this._showErrors(errors);
            return false;
        }
        return isValid;
    },

    _prepareSubmitValues: function (formData, params) {
        this._super(...arguments);
        this.$('[data-question-type="upload"]').each(function () {
            const uploadFile = $(this).data('uploadFile');
            if (uploadFile) {
                params[this.name] = uploadFile;
            } else if (this.dataset.existingFile) {
                params[this.name] = { keep: true };
            } else {
                params[this.name] = '';
            }
        });
    },
});
