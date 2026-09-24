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

import pytz
from dateutil.relativedelta import relativedelta
from collections import defaultdict
from odoo import api, fields, models, _, exceptions


class PlanAllocation(models.Model):
    """Represents planning allocation."""
    _name = 'plan.allocation'
    _description = "Planning Allocation"

    def init(self):
        """Override init to ensure the 'name' column exists in the DB if we are making it stored."""
        self.env.cr.execute("""
            ALTER TABLE plan_allocation ADD COLUMN IF NOT EXISTS name VARCHAR;
        """)

    name = fields.Char(compute='_compute_name', store=True)
    start_datetime = fields.Datetime(string="From", required=True)
    end_datetime = fields.Datetime(string="To", required=True)

    # duration will be calculated based on working hours
    duration = fields.Float(compute='_compute_duration', store=True, readonly=False)

    # percentage of the working day covered by this allocation
    allocation_percentage = fields.Float(
        string="Allocation (%)",
        compute='_compute_allocation_percentage',
        store=True,
        digits=(5, 2),
        help="Percentage of the total working hours in the day covered by this allocation."
    )

    description = fields.Text(help="Planning allocation description")
    employee_id = fields.Many2one('hr.employee', required=True)

    user_id = fields.Many2one(
        'res.users',
        required=True,
        default=lambda self: self.env.user,
        string="Created By"
    )

    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company
    )

    allocation_type_id = fields.Many2one('allocation.type', required=True)
    color = fields.Char(related='allocation_type_id.color')

    is_conflict = fields.Boolean(compute='_compute_conflict_data', store=True)

    auto_filled = fields.Boolean(
        default=False,
        store=False,
        help="Used to suppress warnings when dates are auto-filled."
    )

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to ensure duration is calculated server-side."""
        for vals in vals_list:
            if any(key in vals for key in ['start_datetime', 'end_datetime', 'employee_id', 'allocation_type_id']):
                vals.pop('duration', None)
                vals.pop('allocation_percentage', None)
                vals.pop('name', None)
        return super().create(vals_list)

    def write(self, vals):
        """Override write to force recomputation of duration and percentage if dates change."""
        if any(key in vals for key in ['start_datetime', 'end_datetime', 'employee_id', 'allocation_type_id']):
            vals.pop('duration', None)
            vals.pop('allocation_percentage', None)
            vals.pop('name', None)
        return super().write(vals)


    @api.depends('allocation_type_id', 'employee_id')
    def _compute_name(self):
        """The name of the allocation is computed by using start date and end date."""
        for allocation in self:
            allocation.name = (
                (f"{allocation.employee_id.name} " if allocation.employee_id else '') +
                (f"{allocation.allocation_type_id.name}" if allocation.allocation_type_id else '')
            ) or 'New'



    @api.depends('start_datetime', 'end_datetime', 'employee_id')
    def _compute_duration(self):
        """Compute duration from start date and end date."""
        for allocation in self:
            allocation.duration = allocation._get_duration(
                allocation.start_datetime,
                allocation.end_datetime
            )

    def _get_duration(self, start_datetime, end_datetime):
        """Calculate duration based on employee working hours."""

        if not start_datetime or not end_datetime or end_datetime < start_datetime:
            return 0

        calendar = self.employee_id.resource_calendar_id or self.env.company.resource_calendar_id

        if not calendar:
            return 0

        start_utc = pytz.UTC.localize(start_datetime)
        end_utc = pytz.UTC.localize(end_datetime)

        work_intervals = calendar._work_intervals_batch(
            start_utc,
            end_utc,
            resources=self.employee_id.resource_id
        )
        intervals = work_intervals.get(self.employee_id.resource_id.id, [])
        duration = sum((stop - start).total_seconds() / 3600 for start, stop, meta in intervals)

        return round(duration, 2)

    @api.depends('duration', 'start_datetime', 'employee_id')
    def _compute_allocation_percentage(self):
        for allocation in self:
            if not allocation.start_datetime or not allocation.employee_id or not allocation.duration:
                allocation.allocation_percentage = 0.0
                continue

            calendar = (
                allocation.employee_id.resource_calendar_id
                or allocation.env.company.resource_calendar_id
            )

            if not calendar:
                allocation.allocation_percentage = 0.0
                continue

            # Use employee timezone for day bounds (excl. lunch)
            tz = pytz.timezone(allocation.employee_id.tz or 'UTC')
            start_dt = pytz.UTC.localize(allocation.start_datetime).astimezone(tz)

            day_start = tz.localize(start_dt.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)).astimezone(pytz.UTC)
            day_end = tz.localize(start_dt.replace(hour=23, minute=59, second=59, microsecond=0, tzinfo=None)).astimezone(pytz.UTC)

            work_intervals = calendar._work_intervals_batch(
                day_start,
                day_end,
                resources=allocation.employee_id.resource_id
            )

            intervals = work_intervals.get(allocation.employee_id.resource_id.id, [])
            total_day_hours = sum(
                (iv_end - iv_start).total_seconds() / 3600
                for iv_start, iv_end, _meta in intervals
            )

            if total_day_hours:
                allocation.allocation_percentage = round(
                    (allocation.duration / total_day_hours) * 100, 2
                )
            else:
                allocation.allocation_percentage = 0.0

    # ---------------------------------------------------------
    # CONFLICT CHECK
    # ---------------------------------------------------------

    @api.depends('start_datetime', 'end_datetime', 'employee_id')
    def _compute_conflict_data(self):
        """Compute if the allocation conflicts with other allocations."""
        for allocation in self:
            allocation.is_conflict = allocation._check_overlap()

    def _check_overlap(self):
        """Check if the current allocation overlaps with existing allocations for the same employee."""
        self.ensure_one()

        if not self.start_datetime or not self.end_datetime or not self.employee_id:
            return False

        domain = [
            ('employee_id', '=', self.employee_id.id),
            ('start_datetime', '<', self.end_datetime),
            ('end_datetime', '>', self.start_datetime),
            ('id', '!=', self.id),
        ]

        return bool(self.search_count(domain))

    # ---------------------------------------------------------
    # ONCHANGE WARNINGS
    # ---------------------------------------------------------

    @api.onchange('start_datetime', 'end_datetime')
    def _onchange_check_overlap(self):
        """Warn user if the new allocation overlaps with existing ones."""
        if not self.start_datetime or not self.end_datetime or not self.employee_id:
            return

        if self.auto_filled:
            self.auto_filled = False
            return

        warnings = []

        domain = [
            ('employee_id', '=', self.employee_id.id),
            ('start_datetime', '<', self.end_datetime),
            ('end_datetime', '>', self.start_datetime),
            ('id', '!=', self.id or self._origin.id),
        ]

        if self.search_count(domain):
            warnings.append(
                _("This employee already has another plan scheduled during this time period.")
            )

        if self._check_outside_workhours():
            warnings.append(
                _("The selected time slot falls outside the employee's working hours.")
            )

        if self._check_on_leave():
            warnings.append(
                _("The employee is on approved leave during the selected time period.")
            )

        if warnings:
            return {
                'warning': {
                    'title': _("Scheduling Warning"),
                    'message': '\n'.join(warnings),
                }
            }

    # ---------------------------------------------------------
    # WORK HOURS CHECK
    # ---------------------------------------------------------

    def _check_outside_workhours(self):

        self.ensure_one()

        if not self.start_datetime or not self.end_datetime or not self.employee_id:
            return False

        calendar = self.employee_id.resource_calendar_id or self.env.company.resource_calendar_id
        if not calendar:
            return False

        start_utc = pytz.UTC.localize(self.start_datetime)
        end_utc = pytz.UTC.localize(self.end_datetime)

        day_from = start_utc.replace(hour=0, minute=0, second=0, microsecond=0)
        day_to = end_utc.replace(hour=23, minute=59, second=59, microsecond=0) + relativedelta(days=1)

        work_intervals = calendar._work_intervals_batch(
            day_from,
            day_to,
            resources=self.employee_id.resource_id
        )

        intervals = sorted(
            work_intervals.get(self.employee_id.resource_id.id, []),
            key=lambda x: x[0]
        )

        if not intervals:
            return True

        day_work_start = intervals[0][0]
        day_work_end = intervals[-1][1]

        return start_utc < day_work_start or end_utc > day_work_end

    # ---------------------------------------------------------
    # LEAVE CHECK
    # ---------------------------------------------------------

    def _check_on_leave(self):

        self.ensure_one()

        if not self.start_datetime or not self.end_datetime or not self.employee_id:
            return False

        Leave = self.env['hr.leave']

        domain = [
            ('employee_id', '=', self.employee_id.id),
            ('state', '=', 'validate'),
            ('date_from', '<', self.end_datetime),
            ('date_to', '>', self.start_datetime),
        ]

        return bool(Leave.sudo().search_count(domain))

    @api.constrains('start_datetime', 'end_datetime', 'employee_id')
    def _check_scheduling_constraints(self):
        """Enforce scheduling constraints: work hours and leaves."""
        for record in self:
            if record.auto_filled:
                continue

            errors = []
            if record._check_outside_workhours():
                errors.append(_("The selected time slot falls outside the employee's working hours."))

            if record._check_on_leave():
                errors.append(_("The employee is on approved leave during the selected time period."))

            if errors:
                raise exceptions.ValidationError("\n".join(errors))

    # ---------------------------------------------------------
    # AUTO WORKSHIFT
    # ---------------------------------------------------------

    @api.onchange('employee_id')
    def _onchange_employee_id(self):

        if self.employee_id:

            start, end = self._get_next_workshift()

            if start and end:
                self.auto_filled = True
                self.start_datetime = start
                self.end_datetime = end
                self.duration = self._get_duration(start, end)

    # ---------------------------------------------------------
    # DATE CHANGE
    # ---------------------------------------------------------

    @api.onchange('start_datetime', 'end_datetime')
    def _onchange_dates(self):

        if self.start_datetime and self.end_datetime:
            self.duration = self._get_duration(
                self.start_datetime,
                self.end_datetime
            )

    # ---------------------------------------------------------
    # NEXT WORKSHIFT
    # ---------------------------------------------------------

    def _get_next_workshift(self):

        self.ensure_one()

        if not self.employee_id:
            return False, False

        calendar = self.employee_id.resource_calendar_id or self.env.company.resource_calendar_id

        if not calendar:
            return False, False

        now = fields.Datetime.now().replace(tzinfo=pytz.UTC)

        last_alloc = self.env['plan.allocation'].search(
            [
                ('employee_id', '=', self.employee_id.id),
                ('id', '!=', self._origin.id or False)
            ],
            order='end_datetime desc',
            limit=1
        )

        if last_alloc and last_alloc.end_datetime:

            last_end = last_alloc.end_datetime.replace(tzinfo=pytz.UTC)

            search_from = (last_end + relativedelta(days=1)).replace(
                hour=0,
                minute=0,
                second=0,
                microsecond=0
            )

            search_from = max(
                now.replace(hour=0, minute=0, second=0, microsecond=0),
                search_from
            )

        else:
            search_from = now.replace(hour=0, minute=0, second=0, microsecond=0)

        date_to = search_from + relativedelta(days=14)

        work_intervals = calendar._work_intervals_batch(
            search_from,
            date_to,
            resources=self.employee_id.resource_id
        )

        intervals = list(work_intervals.get(self.employee_id.resource_id.id, []))

        if not intervals:
            return False, False

        by_day = defaultdict(list)

        for iv_start, iv_end, _meta in intervals:
            by_day[iv_start.date()].append((iv_start, iv_end))

        for day in sorted(by_day.keys()):

            day_intervals = sorted(by_day[day], key=lambda x: x[0])

            day_start = day_intervals[0][0]
            day_end = day_intervals[-1][1]

            naive_start = day_start.astimezone(pytz.UTC).replace(tzinfo=None)
            naive_end = day_end.astimezone(pytz.UTC).replace(tzinfo=None)

            return naive_start, naive_end

        return False, False