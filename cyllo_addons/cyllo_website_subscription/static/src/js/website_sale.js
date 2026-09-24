/** @odoo-module **/

import {WebsiteSale} from "@website_sale/js/website_sale";
import {_t} from "@web/core/l10n/translation";
import {ConfirmationDialog} from "@web/core/confirmation_dialog/confirmation_dialog";
import {session} from "@web/session";

WebsiteSale.include({
    selector: '.oe_website_sale',
    events: Object.assign({}, WebsiteSale.prototype.events, {
        'change .js_subscription_plan_select': '_onChangeSubscriptionPlan',
    }),

    /**
     * Handles the change event for the subscription plan selector.
     * * Updates the displayed product price on the page based on the
     * selected plan's data attributes and stores the selected plan ID.
     */

    _onChangeSubscriptionPlan: async function (ev) { // Added 'async' here
        const $select = $(ev.currentTarget);
        const $selectedOption = $select.find('option:selected');
        const $form = $select.closest('form');

        // 1. Get data from form and attributes
        const productTmplId = parseInt($form.find('input[name="product_template_id"]').val());
        const quantity = parseFloat($form.find('input[name="add_qty"]').val() || 1.0);
        const planIdStr = parseInt($form.find('.js_subscription_plan_select').val());

        let price;

        try {
            const result = await this.rpc('/shop/product/get_sub_pricelist_price', {
                product_temp_id: productTmplId,
                plan_id: planIdStr,
                qty: quantity,
            });

            if (result && result.price) {
                price = result.price;
            } else {
                price = $selectedOption.data('price');
            }
        } catch (error) {
            price = $selectedOption.data('price');
        }

        //Update the UI
        const $priceElement = $('.oe_price .oe_currency_value');
        if (price !== undefined) {
            $priceElement.text(parseFloat(price).toFixed(2));
        }

        this.planId = $selectedOption.val();

        // Update the trial highlight box
        if (this.planId) {
            $('.js_trial_highlight_box').addClass('d-none');
            $('.js_trial_highlight_box[data-plan-id="' + this.planId + '"]').removeClass('d-none');
        }

        // Update the recurrence text (e.g. "/ Month")
        const duration = $selectedOption.data('duration');
        const unit = $selectedOption.data('unit');

        if (unit) {
            let formattedUnit = unit;
            if (duration === 1) {
                if (unit === 'months') formattedUnit = 'Month';
                if (unit === 'years') formattedUnit = 'Year';
                if (unit === 'weeks') formattedUnit = 'Week';
                if (unit === 'days') formattedUnit = 'Day';
            }
            const durationText = duration > 1 ? duration + ' ' : '';
            const recurrenceText = ' / ' + durationText + formattedUnit;

            $('.js_subscription_recurrence_text').text(recurrenceText);
            $('.subscription_duration_label_container').text(recurrenceText);
        }
    },

    /**
     * @override
     * This is the method that actually builds the JSON-RPC request.
     * We inject the plan ID here so it reaches the Python kwargs.
     */

    _getOptionalCombinationInfoParam: function (product) {
        // Call the original method using Odoo's legacy _super
        var res = this._super.apply(this, arguments) || {};

        // Append your plan_id
        if (this.planId) {
            res['plan_id'] = this.planId;
        }

        return res;
    },
    /**
     * Ensures data is also sent when clicking 'Add to Cart'
     */
    _updateRootProduct: function ($form, productId) {
        this._super(...arguments);
        const $planSelect = $form.find('.js_subscription_plan_select');
        if ($planSelect.length && this.rootProduct) {
            this.rootProduct.time_based_price_id = parseInt($planSelect.val());
            this.rootProduct.end_date = $form.find('input[name="end_date"]').val();
        }
        // Check for skip_trial flag
        const $skipTrial = $form.find('input[name="skip_trial"]');
        if ($skipTrial.length && $skipTrial.val() === 'true' && this.rootProduct) {
            this.rootProduct.skip_trial = true;
        }
    },

    async _onClickAdd(ev) {
        // We must do this before any 'await' to prevent Odoo from submitting the form.
        ev.preventDefault();
        ev.stopImmediatePropagation();

        const _super = this._super.bind(this);
        const self = this;
        const $form = $(ev.currentTarget).closest('form');
        const productId = parseInt($form.find('input[name="product_id"]').val());

        const planIdStr = $form.find('.js_subscription_plan_select').val();
        const planId = planIdStr ? parseInt(planIdStr) : null;

        try {
            // Fetch cart and product info
            const cartData = await this.rpc('/shop/cart/get_info_json', {
                product_id: productId,
                plan_id: planId
            });

            const hasSubscriptionInCart = cartData.has_subscription;
            const hasNormalInCart = cartData.has_normal;
            const isSubscription = cartData.is_subscription;
            const productHasTrial = cartData.product_has_trial;
            const isPublicUser = !session.user_id;

            // 1. Trial Restriction for Public Users
            if (isPublicUser && productHasTrial) {
                this.call("dialog", "add", ConfirmationDialog, {
                    title: _t("Trial Restriction"),
                    body: _t("You need to be logged in to claim the subscription trial. Do you want to login now?"),
                    confirmLabel: _t("Login & Claim Trial"),
                    cancelLabel: _t("Buy without Trial"),
                    confirm: () => {
                        window.location.href = '/web/login?redirect=' + encodeURIComponent(window.location.href);
                    },
                    cancel: () => {
                        // proceed to add to cart BUT skip trial
                        const $form = $(ev.currentTarget).closest('form');
                        if (!$form.find('input[name="skip_trial"]').length) {
                            $form.append('<input type="hidden" name="skip_trial" value="true"/>');
                        } else {
                            $form.find('input[name="skip_trial"]').val('true');
                        }

                        // We call the original Odoo add-to-cart logic
                        return _super(ev);
                    },
                });
                return Promise.resolve();
            }

            // 2. Logic check for conflicts
            const conflict = (isSubscription && hasNormalInCart) || (!isSubscription && hasSubscriptionInCart);
            if (conflict) {
                // Show the Dialog
                this.call("dialog", "add", ConfirmationDialog, {
                    title: _t("Cart Conflict"),
                    body: _t("Subscription and non-subscription products cannot be purchased together. Do you want to clear your cart and add this item instead?"),
                    confirmLabel: _t("Clear Cart & Add"),
                    cancelLabel: _t("Cancel"),
                    confirm: async () => {
                        // Use your custom clear cart route
                        await this.rpc("/shop/cart/clear", {});
                        // Call the original Odoo add-to-cart logic
                        return _super(ev);
                    },
                    cancel: () => {
                        // Do nothing: close dialog
                    },
                });
                return Promise.resolve(); // Stop further execution
            }
        } catch (error) {
            console.error("Cart compatibility check failed", error);
        }

        //  If no conflict, manually run the super logic
        return _super(ev);
    },

});

