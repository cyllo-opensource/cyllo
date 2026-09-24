/**
 * Appointment Reschedule Page JS
 * Handles slot fetching on the public token-based reschedule page.
 */
function initReschedule() {
    var date_select = $('#date_select');
    if (!date_select.length) return;
    var staff_select = $('#staff_select');
    var resource_select = $('#resource_select');
    var slots_container = $('#slots_container');
    var slots_grid = $('#slots_grid');
    var no_slots_msg = $('#no_slots_msg');
    var submit_btn = $('#submit_btn');
    var is_dynamic_input = $('#is_dynamic_input');
    var dynamic_slot_datetime = $('#dynamic_slot_datetime');
    var predefined_slot_id = $('#predefined_slot_id');
    var appointment_type_id_el = $('#reschedule_appointment_type_id');
    var appointment_type_id = appointment_type_id_el.length ? appointment_type_id_el.val() : null;
    var today = new Date().toISOString().split('T')[0];
    date_select.attr('min', today);

    function fetchSlots() {
        var date = date_select.val();
        if (!date) return;
        var staff_id = staff_select.length ? staff_select.val() : '';
        var resource_id = resource_select.length ? resource_select.val() : '';
        slots_container.show();
        slots_grid.html('<div class="col-12 text-center text-muted"><i class="fa fa-spinner fa-spin"></i> Loading...</div>');
        no_slots_msg.hide();
        submit_btn.prop('disabled', true);
        $.ajax({
            url: '/appointment/' + appointment_type_id + '/availability',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                jsonrpc: '2.0',
                params: { date: date, staff_id: staff_id, resource_id: resource_id },
            }),
            success: function (data) {
                var slots = data.result;
                slots_grid.empty();
                if (!slots || slots.length === 0) {
                    no_slots_msg.show();
                } else {
                    $.each(slots, function (index, slot) {
                        var div = $('<div>').addClass('col-md-3 col-sm-4 col-6');
                        var btn = $('<button>')
                            .attr('type', 'button')
                            .addClass('btn btn-outline-primary w-100 text-nowrap slot-btn mb-2')
                            .css('border-radius', '8px')
                            .text(slot.time);
                        if (slot.is_full) {
                            btn.prop('disabled', true)
                               .addClass('disabled opacity-50')
                               .css('cursor', 'not-allowed');
                        } else {
                            btn.on('click', function () {
                                $('.slot-btn')
                                    .removeClass('btn-primary text-white')
                                    .addClass('btn-outline-primary');
                                $(this)
                                    .addClass('btn-primary text-white')
                                    .removeClass('btn-outline-primary');
                                if (slot.is_dynamic) {
                                    is_dynamic_input.val('true');
                                    dynamic_slot_datetime.val(slot.start_datetime);
                                    predefined_slot_id.val('');
                                } else {
                                    is_dynamic_input.val('false');
                                    predefined_slot_id.val(slot.id);
                                    dynamic_slot_datetime.val('');
                                }
                                submit_btn.prop('disabled', false);
                            });
                        }
                        div.append(btn);
                        slots_grid.append(div);
                    });
                }
            }
        });
    }
    date_select.on('change', fetchSlots);
    if (staff_select.length) staff_select.on('change', fetchSlots);
    if (resource_select.length) resource_select.on('change', fetchSlots);
}
$(document).ready(function () {
    initReschedule();
});
