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

import re
from collections import defaultdict
from datetime import timedelta

from odoo import fields, models


class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'

    carbon_activity_ids = fields.One2many('carbon.activity', 'workorder_id', string='Carbon Activities')

    def write(self, vals):
        res = super().write(vals)
        if any(f in vals for f in ('duration', 'state', 'date_start', 'date_finished', 'time_ids')):
            self._update_carbon_activities()
        return res

    def button_start(self):
        res = super().button_start()
        self._update_carbon_activities()
        return res

    def button_pending(self):
        res = super().button_pending()
        self._update_carbon_activities()
        return res

    def button_finish(self):
        res = super().button_finish()
        self._update_carbon_activities()
        return res

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _get_carbon_operation(self):
        """Return the routing operation whose carbon lines drive this work order."""
        self.ensure_one()
        operation = self.operation_id
        if not operation:
            all_routing_ops = self.env['mrp.routing.workcenter'].search([
                ('company_id', '=', self.company_id.id)
            ])
            for op in all_routing_ops:
                if op.name and re.search(f'^{re.escape(self.name)}$', op.name, re.IGNORECASE):
                    operation = op
                    break
        return operation

    def _get_duration_hours_per_day(self):
        """Split the real work duration across the actual calendar days it happened.

        Emissions must be attributed to the day the work was really performed,
        so we read the raw productivity blocks (``time_ids``) instead of the
        planned dates. A block that spans midnight is split at midnight
        (option B), so each day only gets the hours worked within it. Dates are
        computed in the user's timezone. Returns ``{date: hours}``.
        """
        self.ensure_one()
        per_day = defaultdict(float)
        now = fields.Datetime.now()
        for block in self.time_ids:
            start = block.date_start
            if not start:
                continue
            # An open (running) block is counted up to "now".
            end = block.date_end or now
            if end <= start:
                continue
            start_local = fields.Datetime.context_timestamp(self, start)
            end_local = fields.Datetime.context_timestamp(self, end)
            cursor = start_local
            while cursor < end_local:
                next_midnight = (cursor + timedelta(days=1)).replace(
                    hour=0, minute=0, second=0, microsecond=0)
                seg_end = min(end_local, next_midnight)
                hours = (seg_end - cursor).total_seconds() / 3600.0
                if hours > 0:
                    per_day[cursor.date()] += hours
                cursor = seg_end
        return per_day

    def _get_or_create_carbon_calc(self, activity_date):
        """Find the draft calculation for a day/company, creating a flagged one if missing.

        Work order emissions may only land in a Draft calculation: when the day's
        record is already submitted/approved/done, a new draft one is opened.
        """
        self.ensure_one()
        return self.env['carbon.calc']._get_or_create_draft_calc(
            activity_date, self.company_id, extra_vals={'auto_generated': True})

    def _update_carbon_activities(self):
        for order in self:
            order._sync_carbon_activities()

    def _sync_carbon_activities(self):
        """Rebuild this work order's carbon activities from its real work sessions.

        For every day the operation was actually worked, and for every emission
        factor of every configured source, one ``carbon.activity`` holds that
        day's hours. The method is idempotent: it updates matching activities,
        removes the ones that no longer apply, and deletes any auto-generated
        calculation record it leaves empty.
        """
        self.ensure_one()
        Activity = self.env['carbon.activity']

        old_activities = Activity.search([('workorder_id', '=', self.id)])
        old_calcs = old_activities.mapped('calculation_id')

        operation = self._get_carbon_operation()
        per_day = self._get_duration_hours_per_day() if operation else {}
        # Only keep days that carry real work.
        per_day = {day: hours for day, hours in per_day.items() if hours > 0.001}

        unit_hr = self.env['carbon.unit'].search([
            ('name', 'ilike', 'hr'),
            ('company_id', '=', self.company_id.id),
        ], limit=1)

        kept = Activity.browse()
        if operation and per_day:
            calc_by_day = {day: self._get_or_create_carbon_calc(day) for day in per_day}
            for line in operation.carbon_line_ids:
                source = line.source_id
                if not source:
                    continue
                all_factors = source.air_factor_ids + source.sound_factor_ids + source.water_factor_ids
                uom_id = unit_hr.id if unit_hr else source.activity_unit.id
                for factor in all_factors:
                    for day, hours in per_day.items():
                        # A factor outside its validity window cannot be used that day.
                        if not factor._is_valid_on(day):
                            continue
                        calc = calc_by_day[day]
                        vals = {
                            'name': self.name,
                            'date': day,
                            'calculation_id': calc.id,
                            'workorder_id': self.id,
                            'source_id': source.id,
                            'factor_id': factor.id,
                            'quantity': hours,
                            'uom_id': uom_id,
                            'company_id': self.company_id.id,
                        }
                        existing = Activity.search([
                            ('workorder_id', '=', self.id),
                            ('source_id', '=', source.id),
                            ('factor_id', '=', factor.id),
                            ('date', '=', day),
                            ('company_id', '=', self.company_id.id),
                        ], limit=1)
                        if existing:
                            # Done activities, and those already locked into a
                            # closed calculation, are left untouched.
                            if existing._is_carbon_locked():
                                kept |= existing
                                continue
                            existing.write(vals)
                            kept |= existing
                        else:
                            kept |= Activity.create(vals)

        # Drop activities that no longer correspond to a real work day/source/factor,
        # keeping the ones that are no longer ours to change.
        stale = (old_activities - kept).filtered(lambda a: not a._is_carbon_locked())
        if stale:
            stale.unlink()

        # Remove auto-generated calculation records that we emptied out.
        candidate_calcs = old_calcs | kept.mapped('calculation_id')
        empty_auto = candidate_calcs.filtered(
            lambda c: c.auto_generated and c.state == 'draft' and not c.carbon_activity_ids)
        if empty_auto:
            empty_auto.unlink()
