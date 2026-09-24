/**
 * Appointment Booking Page JS
 * Handles slot fetching, attendee count and additional attendee fields.
 */
function initBooking() {
    const date_select = $('#date_select');
    if (!date_select.length) return;
    const staff_select = $('#staff_select');
    const resource_select = $('#resource_select');
    const slots_container = $('#slots_container');
    const slots_grid = $('#slots_grid');
    const no_slots_msg = $('#no_slots_msg');
    const submit_btn = $('#submit_btn');
    const is_dynamic_input = $('#is_dynamic_input');
    const dynamic_slot_datetime = $('#dynamic_slot_datetime');
    const predefined_slot_id = $('#predefined_slot_id');
    const appointment_type_id_el = $('#appointment_type_id_value');
    const appointment_type_id = appointment_type_id_el.length ? appointment_type_id_el.val() : null;
    const type_max_attendees_el = $('#type_max_attendees_value');
    const type_max_attendees = parseInt(type_max_attendees_el.length ? type_max_attendees_el.val() : '1') || 1;
    const today = new Date().toISOString().split('T')[0];
    date_select.attr('min', today);
    function fetchSlots() {
        const date = date_select.val();
        if (!date) return;
        let staff_id = '';
        if (staff_select.length) {
            staff_id = staff_select.val();
        }
        let resource_id = '';
        if (resource_select.length) {
            resource_id = resource_select.val();
        }
        slots_container.show();
        slots_grid.html('<div class="col-12 text-center text-muted"><i class="fa fa-spinner fa-spin"/> Loading availability...</div>');
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
                if (data.error) {
                    console.error('RPC Error:', data.error);
                    slots_grid.empty();
                    return;
                }
                const slots = data.result;
                slots_grid.empty();

                if (!slots || slots.length === 0) {
                    no_slots_msg.show();
                } else {
                    $.each(slots, function (index, slot) {
                        const div = $('<div>').addClass('col-md-3 col-sm-4 col-6');
                        const wrapper = $('<div>').css({
                            'display': 'inline-block',
                            'width': '100%'
                        });
                        const btn = $('<button>')
                            .attr('type', 'button')
                            .addClass('btn btn-outline-primary w-100 text-nowrap slot-btn mb-2')
                            .css('border-radius', '8px')
                            .text(slot.time)
                            .attr({
                                'data-is_dynamic': slot.is_dynamic,
                                'data-id': slot.id,
                                'data-datetime': slot.start_datetime
                            });
                        if (slot.is_full || slot.is_past) {
                            btn.prop('disabled', true)
                               .addClass('disabled opacity-50')
                               .css('cursor', 'not-allowed');
                             wrapper.attr(
                                'title',
                                slot.is_past
                                    ? 'This time slot has already passed'
                                    : 'This slot is fully booked'
                            );
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
                                    if (slot.staff_id && staff_select.length) {
                                        staff_select.val(slot.staff_id);
                                    }
                                    if (slot.resource_id && resource_select.length) {
                                        resource_select.val(slot.resource_id);
                                    }
                                }
                                const maxSpots = Math.min(slot.spots, type_max_attendees);
                                const attSelect = $('#attendee_count');
                                const attSection = $('#attendees_section');
                                if (attSelect.length && maxSpots > 1) {
                                    attSection.show();
                                    attSelect.empty();
                                    for (let i = 1; i <= maxSpots; i++) {
                                        const opt = $('<option>').val(i).text(i === 1 ? '1 Person' : i + ' People');
                                        attSelect.append(opt);
                                    }
                                    $('#additional_attendees_container').empty();
                                } else if (attSection.length) {
                                    attSection.hide();
                                    attSelect.html('<option value="1">1 Person</option>');
                                    $('#additional_attendees_container').empty();
                                }
                                submit_btn.prop('disabled', false);
                            });
                        }
                        wrapper.append(btn);
                        div.append(wrapper);
                        slots_grid.append(div);
                    });
                }
            }
        });
    }
    date_select.on('change', fetchSlots);
    if (staff_select.length) staff_select.on('change', fetchSlots);
    if (resource_select.length) resource_select.on('change', fetchSlots);
    const attendee_count_el = $('#attendee_count');
    const extra_container = $('#additional_attendees_container');
    if (attendee_count_el.length && extra_container.length) {
        attendee_count_el.on('change', function () {
            const count = parseInt($(this).val()) || 1;
            extra_container.empty();
            if (count > 1) {
                let html = '<hr class="my-4"/><h5 class="fw-bold mb-3">Additional Attendees</h5>';
                for (let i = 2; i <= count; i++) {
                    html += `
                        <div class="card bg-white shadow-sm border mb-3" style="border-radius: 8px;">
                            <div class="card-body">
                                <h6 class="fw-bold text-muted mb-3">Attendee ${i}</h6>
                                <div class="row">
                                    <div class="col-md-4 mb-2">
                                        <label class="form-label small">Name</label>
                                        <input type="text" name="name_${i}" class="form-control" required style="border-radius: 8px; border:1px solid #dee2e6;"/>
                                    </div>
                                    <div class="col-md-4 mb-2">
                                        <label class="form-label small">Email</label>
                                        <input type="email" name="email_${i}" class="form-control" required style="border-radius: 8px; border:1px solid #dee2e6;"/>
                                    </div>
                                    <div class="col-md-4 mb-2">
                                        <label class="form-label small">Phone</label>
                                        <input type="tel" name="phone_${i}" class="form-control" required style="border-radius: 8px; border:1px solid #dee2e6;"/>
                                    </div>
                                </div>
                            </div>
                        </div>`;
                }
                extra_container.html(html);
            }
        });
    }
}
$(document).ready(function () {
    initBooking();
});
