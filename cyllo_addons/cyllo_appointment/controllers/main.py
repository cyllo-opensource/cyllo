# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cyllo(<https://www.cyllo.com>)
#    Author: Cyllo(<https://www.cyllo.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request
from datetime import datetime, timedelta
from odoo import fields
import pytz
from odoo.addons.website_sale.controllers.main import WebsiteSale


class AppointmentWebsiteController(http.Controller):

    @http.route('/appointment', type='http', auth='public', website=True)
    def appointment_list(self, **kw):
        """List all published appointment types."""
        appointment_types = request.env['appointment.type'].sudo().search(
            [('is_published', '=', True)])
        return request.render('cyllo_appointment.appointment_type_list', {
            'appointment_types': appointment_types,
        })

    @http.route(['/appointment/<int:appointment_type_id>'],
                type='http', auth='public', website=True)
    def appointment_details(self, appointment_type_id, **kw):
        """Show selection form (Staff/Resource, Date, Time) based on scheduling type."""
        appointment_type = request.env['appointment.type'].sudo().browse(appointment_type_id)
        if not appointment_type.exists():
            return request.redirect('/appointment')
        if not appointment_type.is_published and request.env.user._is_public():
            return request.redirect('/appointment')

        staffs = False
        if appointment_type.require_staff:
            staffs = appointment_type.sudo().staff_ids or request.env['hr.employee'].sudo().search([])
        resources = False
        if appointment_type.require_resource:
            resources = appointment_type.sudo().resource_ids or request.env['appointment.resource'].sudo().search([])
        values = {
            'main_object': appointment_type,
            'appointment_type': appointment_type,
            'scheduling_type': appointment_type.scheduling_type,
            'staffs': staffs,
            'resources': resources,
        }
        return request.render('cyllo_appointment.appointment_selection', values)

    @http.route(['/appointment/<int:appointment_type_id>/availability'],type='json', auth='public', website=True)
    def appointment_availability(self, appointment_type_id, date, staff_id=None, resource_id=None, **kw):
        """Returns available slots dynamically or predefined slots based on date."""
        appointment_type = request.env['appointment.type'].sudo().browse(appointment_type_id)
        if not appointment_type.exists():
            return []
        target_date = datetime.strptime(date, "%Y-%m-%d").date()
        now_utc = datetime.utcnow()

        if appointment_type.scheduling_type == 'predefined':
            # Predefined slots
            domain = [
                ('appointment_type_id', '=', appointment_type.id),
                ('start_datetime', '>=', datetime.combine(target_date, datetime.min.time())),
                ('end_datetime', '<=',
                 datetime.combine(target_date, datetime.max.time())),
            ]
            if staff_id:
                domain.append(('staff_id', '=', int(staff_id)))
            if resource_id:
                domain.append(('resource_id', '=', int(resource_id)))
            slots = request.env['appointment.slot'].sudo().search(domain)
            available_slots = []
            for slot in slots:
                user_tz = pytz.timezone(request.context.get('tz') or 'UTC')
                start_dt = pytz.utc.localize(slot.start_datetime).astimezone(
                    user_tz)
                available_slots.append({
                    'id': slot.id,
                    'time': start_dt.strftime('%I:%M %p'),
                    'spots': slot.available_count,
                    'is_full': slot.available_count <= 0,
                    'start_datetime': slot.start_datetime.strftime(
                        '%Y-%m-%d %H:%M:%S'),
                    'is_dynamic': False,
                    'is_past': slot.start_datetime < now_utc,
                    'staff_id': slot.staff_id.id if slot.staff_id else False,
                    'resource_id': slot.resource_id.id if slot.resource_id else False,
                })
            return available_slots
        else:
            user_tz = pytz.timezone(request.context.get('tz') or 'UTC')
            interval_minutes = int(appointment_type.slot_interval)
            duration_hours = appointment_type.duration
            calendar = request.env['resource.calendar']
            if staff_id:
                staff = request.env['hr.employee'].sudo().browse(int(staff_id))
                calendar = staff.resource_calendar_id
            if not calendar and resource_id:
                resource = request.env['appointment.resource'].sudo().browse(int(resource_id))
                calendar = resource.working_hours_id
            if not calendar:
                calendar = appointment_type.working_hours_id
            available_slots = []
            valid_intervals = []
            if calendar:
                attendances = calendar.attendance_ids.filtered(lambda a: a.dayofweek == str(target_date.weekday()))
                for att in attendances:
                    h_from, m_from = divmod(att.hour_from * 60, 60)
                    h_to, m_to = divmod(att.hour_to * 60, 60)
                    valid_intervals.append((
                        datetime.combine(target_date, datetime.min.time().replace(hour=int(h_from), minute=int(m_from))),
                        datetime.combine(target_date, datetime.min.time().replace(hour=int(h_to), minute=int(m_to)))
                    ))
            else:
                valid_intervals.append((
                    datetime.combine(target_date, datetime.min.time().replace(hour=9)),
                    datetime.combine(target_date, datetime.min.time().replace(hour=17))
                ))
            for interval_start, interval_end in valid_intervals:
                current_time = interval_start
                while current_time + timedelta(hours=duration_hours) <= interval_end:
                    slot_end = current_time + timedelta(hours=duration_hours)
                    utc_start = user_tz.localize(current_time).astimezone(
                        pytz.utc).replace(tzinfo=None)
                    utc_end = user_tz.localize(slot_end).astimezone(
                        pytz.utc).replace(tzinfo=None)
                    domain = [
                        ('state', 'in', ['confirmed', 'in_progress']),
                        ('start_datetime', '<', utc_end),
                        ('end_datetime', '>', utc_start),
                    ]
                    if staff_id:
                        domain.append(('staff_id', '=', int(staff_id)))
                    if resource_id:
                        domain.append(('resource_id', '=', int(resource_id)))
                    overlapping = request.env[
                        'appointment.appointment'].sudo().search(domain, limit=1)
                    available_slots.append({
                        'id': f"{utc_start.strftime('%Y-%m-%d %H:%M:%S')}",
                        'time': current_time.strftime('%I:%M %p'),
                        'spots': 0 if overlapping else 1,
                        'is_full': bool(overlapping),
                        'start_datetime': utc_start.strftime('%Y-%m-%d %H:%M:%S'),
                        'is_dynamic': True,
                        'is_past': utc_start < now_utc,
                    })
                    current_time += timedelta(minutes=interval_minutes)

            return available_slots

    @http.route( ['/appointment/<int:appointment_type_id>/submit'],
        type='http', auth='public', website=True, methods=['POST'], csrf=True)
    def appointment_submit(self, appointment_type_id, **post):
        """Process the booking form and create logical structures."""
        appointment_type = request.env['appointment.type'].sudo().browse(appointment_type_id)
        if not appointment_type.exists():
            return request.redirect('/appointment')
        # 1. Partner Logic
        partner_name = post.get('name')
        partner_email = post.get('email')
        partner_phone = post.get('phone')
        Partner = request.env['res.partner'].sudo()
        partner = Partner.search([('email', '=', partner_email)], limit=1)
        if not partner:
            partner = Partner.create({
                'name': partner_name,
                'email': partner_email,
                'phone': partner_phone,
            })
        attendee_count = int(post.get('attendee_count', 1))
        # 2. Appointment Data
        val = {
            'appointment_type_id': appointment_type.id,
            'partner_id': partner.id,
            'booker_name': partner_name,
            'customer_notes': post.get('notes'),
            'state': 'pending_payment' if appointment_type.is_paid else 'confirmed',
            'attendee_count': attendee_count,
        }
        attendee_ids = []
        if attendee_count > 1:
            for i in range(2, attendee_count + 1):
                a_name = post.get(f'name_{i}')
                a_email = post.get(f'email_{i}')
                a_phone = post.get(f'phone_{i}')
                if a_name and a_email:
                    a_partner = Partner.search([('email', '=', a_email)],
                                               limit=1)
                    if not a_partner:
                        a_partner = Partner.create({
                            'name': a_name,
                            'email': a_email,
                            'phone': a_phone,
                        })
                    attendee_ids.append(a_partner.id)
        if attendee_ids:
            val['attendee_ids'] = [(6, 0, attendee_ids)]
        if post.get('staff_id'):
            val['staff_id'] = int(post.get('staff_id'))
        if post.get('resource_id'):
            val['resource_id'] = int(post.get('resource_id'))
        if post.get('is_dynamic') == 'true':
            # Dynamic creation
            start_dt = datetime.strptime(post.get('dynamic_slot_datetime'),
                                         '%Y-%m-%d %H:%M:%S')
            val['start_datetime'] = start_dt
            val['end_datetime'] = start_dt + timedelta(
                hours=appointment_type.duration)
        else:
            # Predefined slot creation
            slot_id = int(post.get('slot_id'))
            slot = request.env['appointment.slot'].sudo().browse(slot_id)
            val['slot_id'] = slot.id
            val['start_datetime'] = slot.start_datetime
            val['end_datetime'] = slot.end_datetime

        try:
            with request.env.cr.savepoint():
                appointment = request.env['appointment.appointment'].sudo().create(val)
                request.env.flush_all()
        except ValidationError as e:
            staffs = False
            if appointment_type.require_staff:
                staffs = appointment_type.sudo().staff_ids or request.env['hr.employee'].sudo().search([])
            resources = False
            if appointment_type.require_resource:
                resources = appointment_type.sudo().resource_ids or request.env['appointment.resource'].sudo().search([])
            values = {
                'main_object': appointment_type,
                'appointment_type': appointment_type,
                'scheduling_type': appointment_type.scheduling_type,
                'staffs': staffs,
                'resources': resources,
                'error_message': str(e),
            }
            return request.render('cyllo_appointment.appointment_selection',
                                  values)

        if appointment_type.is_paid and appointment_type.product_id:
            order = request.website.sale_get_order(force_create=True)
            if not order:
                return request.redirect('/shop/cart')
            if order.partner_id != partner:
                order.sudo().write({'partner_id': partner.id})
            appointment.sale_order_id = order.id
            order._cart_update(
                product_id=appointment_type.product_id.id,
                add_qty=1
            )
            return request.redirect('/shop/cart')

        return request.render('cyllo_appointment.appointment_success', {
            'appointment': appointment,
        })

    # -----------------------------------------------------------------------
    # Website Management (Reschedule / Cancel) via access token
    # -----------------------------------------------------------------------
    def _get_appointment_by_token(self, token):
        """Helper: look up appointment by access_token using sudo."""
        return request.env['appointment.appointment'].sudo().search(
            [('access_token', '=', token)], limit=1
        )

    @http.route('/appointment/manage/<string:token>', type='http',
                auth='public', website=True)
    def appointment_manage(self, token, **kw):
        """Landing page: show appointment details with Reschedule / Cancel buttons."""
        appointment = self._get_appointment_by_token(token)
        if not appointment:
            return request.render('http_routing.403')
        now = fields.Datetime.now()
        atype = appointment.appointment_type_id
        can_reschedule = (
                atype.allow_reschedule and
                appointment.state == 'confirmed' and
                (not atype.reschedule_deadline_hours or
                 appointment.start_datetime - timedelta(
                            hours=atype.reschedule_deadline_hours) > now)
        )
        can_cancel = False
        if appointment.state == 'confirmed':
            if atype.cancel_policy == 'anytime':
                can_cancel = True
            elif atype.cancel_policy == 'up_to':
                deadline = appointment.start_datetime - timedelta(hours=atype.cancel_deadline_hours)
                can_cancel = (now < deadline)

        return request.render('cyllo_appointment.appointment_manage', {
            'appointment': appointment,
            'token': token,
            'can_reschedule': can_reschedule,
            'can_cancel': can_cancel,
        })

    @http.route('/appointment/manage/<string:token>/reschedule', type='http',
                auth='public', website=True)
    def appointment_reschedule_page(self, token, **kw):
        """Show the reschedule form (same slot picker, pre-seeded with appointment type)."""
        appointment = self._get_appointment_by_token(token)
        if not appointment or appointment.state != 'confirmed':
            return request.redirect('/appointment')
        atype = appointment.appointment_type_id
        if not atype.allow_reschedule:
            return request.redirect('/appointment/manage/' + token)
        staffs = False
        if atype.require_staff:
            staffs = atype.sudo().staff_ids or request.env['hr.employee'].sudo().search([])
        resources = False
        if atype.require_resource:
            resources = atype.sudo().resource_ids or request.env['appointment.resource'].sudo().search([])

        return request.render('cyllo_appointment.appointment_reschedule', {
            'appointment': appointment,
            'appointment_type': atype,
            'token': token,
            'staffs': staffs,
            'resources': resources,
        })

    @http.route('/appointment/manage/<string:token>/reschedule/submit',
                type='http', auth='public', website=True, methods=['POST'],
                csrf=True)
    def appointment_reschedule_submit(self, token, **post):
        """Process the reschedule form submission."""
        appointment = self._get_appointment_by_token(token)
        if not appointment or appointment.state != 'confirmed':
            return request.redirect('/appointment')
        atype = appointment.appointment_type_id
        now = fields.Datetime.now()
        # Deadline check
        if atype.reschedule_deadline_hours:
            deadline = appointment.start_datetime - timedelta(
                hours=atype.reschedule_deadline_hours)
            if now > deadline:
                return request.render('cyllo_appointment.appointment_manage', {
                    'appointment': appointment,
                    'token': token,
                    'can_reschedule': False,
                    'can_cancel': False,
                    'error_message': 'Rescheduling deadline has passed.',
                })
        # Build new datetime values
        try:
            if post.get('is_dynamic') == 'true':
                new_start = datetime.strptime(post.get('dynamic_slot_datetime'),
                                              '%Y-%m-%d %H:%M:%S')
                new_end = new_start + timedelta(hours=atype.duration)
                new_slot_id = False
            else:
                slot_id = int(post.get('slot_id'))
                slot = request.env['appointment.slot'].sudo().browse(slot_id)
                new_start = slot.start_datetime
                new_end = slot.end_datetime
                new_slot_id = slot.id
            # Save original start
            if not appointment.original_start_datetime:
                appointment.sudo().write(
                    {'original_start_datetime': appointment.start_datetime})
            vals = {
                'start_datetime': new_start,
                'end_datetime': new_end,
                'is_rescheduled': True,
                'reschedule_count': appointment.reschedule_count + 1,
            }
            if new_slot_id:
                vals['slot_id'] = new_slot_id
            if post.get('staff_id'):
                vals['staff_id'] = int(post.get('staff_id'))
            if post.get('resource_id'):
                vals['resource_id'] = int(post.get('resource_id'))
            appointment.sudo().write(vals)
        except (ValidationError, ValueError) as e:
            staffs = False
            if atype.require_staff:
                staffs = atype.sudo().staff_ids or request.env['hr.employee'].sudo().search([])
            resources = False
            if atype.require_resource:
                resources = atype.sudo().resource_ids or request.env['appointment.resource'].sudo().search([])

            return request.render('cyllo_appointment.appointment_reschedule', {
                'appointment': appointment,
                'appointment_type': atype,
                'token': token,
                'staffs': staffs,
                'resources': resources,
                'error_message': str(e),
            })
        # Recalculate based on new start_datetime
        can_reschedule = (
                atype.allow_reschedule and
                appointment.state == 'confirmed' and
                (not atype.reschedule_deadline_hours or
                 appointment.start_datetime - timedelta(
                            hours=atype.reschedule_deadline_hours) > now)
        )
        can_cancel = False
        if appointment.state == 'confirmed':
            if atype.cancel_policy == 'anytime':
                can_cancel = True
            elif atype.cancel_policy == 'up_to':
                deadline = appointment.start_datetime - timedelta(hours=atype.cancel_deadline_hours)
                can_cancel = (now < deadline)

        return request.render('cyllo_appointment.appointment_manage', {
            'appointment': appointment,
            'token': token,
            'can_reschedule': can_reschedule,
            'can_cancel': can_cancel,
            'success_message': 'Your appointment has been successfully rescheduled.',
        })

    @http.route('/appointment/manage/<string:token>/cancel', type='http',
                auth='public', website=True, methods=['POST'], csrf=True)
    def appointment_cancel_submit(self, token, **post):
        """Process online cancellation."""
        appointment = self._get_appointment_by_token(token)
        if not appointment or appointment.state != 'confirmed':
            return request.redirect('/appointment')
        atype = appointment.appointment_type_id
        now = fields.Datetime.now()
        if atype.cancel_policy == 'never':
            return request.redirect('/appointment/manage/' + token)
        if atype.cancel_policy == 'up_to':
            deadline = appointment.start_datetime - timedelta(
                hours=atype.cancel_deadline_hours)
            if now > deadline:
                return request.render('cyllo_appointment.appointment_manage', {
                    'appointment': appointment,
                    'token': token,
                    'can_reschedule': False,
                    'can_cancel': False,
                    'error_message': 'Cancellation deadline has passed. Please contact us directly.',
                })
        appointment.sudo().write({
            'state': 'cancelled',
            'cancellation_reason': post.get('reason', ''),
            'cancelled_by': 'customer',
        })
        return request.render('cyllo_appointment.appointment_cancelled', {
            'appointment': appointment,
        })

class WebsiteSaleAppointment(WebsiteSale):
    @http.route()
    def shop_payment_confirmation(self, **post):
        res = super(WebsiteSaleAppointment, self).shop_payment_confirmation(**post)
        sale_order_id = request.session.get('sale_last_order_id')
        if sale_order_id:
            order = request.env['sale.order'].sudo().browse(sale_order_id)
            appointment = request.env['appointment.appointment'].sudo().search([('sale_order_id', '=', order.id)], limit=1)
            if appointment:
                return request.render('cyllo_appointment.appointment_success', {
                    'appointment': appointment,
                })
        return res

