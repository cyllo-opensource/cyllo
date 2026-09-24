/** @odoo-module **/
import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.OwlCarousel = publicWidget.Widget.extend({
    selector: '.owl-carousel',
    start: function () {
        this.$el.owlCarousel({
            loop: true,
            margin: 10,
            nav: false,
            dots: true,
            items: 1,
            autoplay: true,
            autoplayTimeout: 3000,
            autoplayHoverPause: true
        });
    },
});