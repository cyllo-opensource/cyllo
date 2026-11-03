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
import datetime

from dateutil.relativedelta import relativedelta
from odoo import api, fields, models


class HrEmployee(models.Model):
    """
       Extend the functionality of the hr.employee model.
       This class inherits from the hr.employee model to add custom functionality.
       """
    _inherit = 'hr.employee'

    @api.model
    def get_hr_dashboard_data(self, date_filter='year'):
        """
        Fetch data for the HR dashboard.
        Returns:
            dict: Dashboard metrics and lists.
        """
        today = fields.Date.today()
        start_date = today
        end_date = today

        if date_filter == 'today':
            start_date = today
            end_date = today
        elif date_filter == 'week':
            start_date = today - relativedelta(days=today.weekday())  # Monday
            end_date = start_date + relativedelta(days=6)  # Sunday
        elif date_filter == 'month':
            start_date = today.replace(day=1)
            end_date = start_date + relativedelta(months=1, days=-1)
        elif date_filter == 'year':
            start_date = today.replace(month=1, day=1)
            end_date = start_date + relativedelta(years=1, days=-1)

        # Previous period of the same length, used for the KPI delta badges
        # (e.g. "12 Last month" / "3 Last week").
        period_days = max((end_date - start_date).days + 1, 1)
        prev_start = start_date - relativedelta(days=period_days)
        prev_end = start_date - relativedelta(days=1)

        prev_labels = {'today': 'Yesterday', 'week': 'Last week',
                       'month': 'Last month', 'year': 'Last year'}
        kpi_compare_label = prev_labels.get(date_filter, 'Last period')

        def hr_delta(current, previous):
            """Returns (previous_value, changed_pct) for a KPI card."""
            try:
                current_n = float(current)
                previous_n = float(previous)
            except (TypeError, ValueError):
                return previous, 0
            if previous_n:
                changed = round((current_n - previous_n) / previous_n * 100)
            elif current_n > 0:
                changed = 100
            else:
                changed = 0
            return previous, changed

        # Total Employees (Always total)
        total_employees = self.search_count([('active', '=', True)])
        # Workforce as it was at the start of the period (for "N Last month")
        total_employees_prev = self.search_count([
            ('active', '=', True),
            ('create_date', '<', datetime.datetime.combine(
                start_date, datetime.time.min))
        ]) if 'create_date' in self._fields else total_employees
        total_employees_compare, total_employees_pct = hr_delta(
            total_employees, total_employees_prev)

        # Attendance Rate (Average for the period)
        attendance_rate = 0
        attendance_rate_compare, attendance_rate_pct = 0, 0
        if 'hr.attendance' in self.env:
            # For 'today', we look at all unique employees who checked in today
            def attendance_rate_for(a_start, a_end):
                attended = self.env['hr.attendance'].read_group(
                    [('check_in', '>=', a_start), ('check_in', '<=', a_end)],
                    ['employee_id'], ['employee_id'])
                return (len(attended) / total_employees * 100) if total_employees > 0 else 0

            attendance_rate = attendance_rate_for(start_date, end_date)
            attendance_rate = int(attendance_rate) if float(attendance_rate).is_integer() else round(attendance_rate, 2)
            attendance_rate_compare, attendance_rate_pct = hr_delta(
                attendance_rate, round(attendance_rate_for(prev_start, prev_end), 2))
            attendance_rate_compare = int(attendance_rate_compare) if float(attendance_rate_compare).is_integer() else attendance_rate_compare

        # Total Job Applied (Recruitment)
        job_applied_count = 0
        try:
            if 'hr.applicant' in self.env:
                job_applied_count = self.env['hr.applicant'].search_count([
                    ('create_date', '>=', start_date),
                    ('create_date', '<=', end_date)
                ])
        except Exception:
            pass
        job_applied_compare, job_applied_pct = hr_delta(
            job_applied_count,
            self.env['hr.applicant'].search_count([
                ('create_date', '>=', prev_start),
                ('create_date', '<=', prev_end)
            ]) if 'hr.applicant' in self.env else 0)

        # Upcoming Time Off (validated leaves starting today or later)
        upcoming_timeoff_count = self.env['hr.leave'].search_count([
            ('state', '=', 'validate'), ('request_date_from', '>=', today)
        ]) if 'hr.leave' in self.env else 0
        upcoming_timeoff_compare, upcoming_timeoff_pct = hr_delta(
            upcoming_timeoff_count,
            self.env['hr.leave'].search_count([
                ('state', '=', 'validate'),
                ('request_date_from', '>=', prev_start),
                ('request_date_from', '<=', prev_end)
            ]) if 'hr.leave' in self.env else 0)

        # Employee Status Breakdown (By Job Position) - Not affected by date filter
        status_data = self.env['hr.job'].search_read([], ['name', 'no_of_employee'])
        employee_status_labels = [s['name'] for s in status_data if s['no_of_employee'] > 0]
        employee_status_counts = [s['no_of_employee'] for s in status_data if s['no_of_employee'] > 0]

        # Monthly Attendance Trend (Last 6 Months) - Static trend
        attendance_trend_labels = []
        attendance_trend_data = []
        if 'hr.attendance' in self.env:
            for month in range(5, -1, -1):
                month_date = today - relativedelta(months=month)
                month_label = month_date.strftime('%b')
                attendance_trend_labels.append(month_label)
                month_start = month_date.replace(day=1)
                month_end = month_start + relativedelta(months=1)
                attendance_count = self.env['hr.attendance'].search_count([
                    ('check_in', '>=', month_start),
                    ('check_in', '<', month_end),
                ])
                attendance_trend_data.append(attendance_count)

        # Pending Payslips
        pending_payslips_list = []
        if 'employee.payslip' in self.env:
            payslip_domain = [('state', '=', 'waiting')]
            if date_filter == 'today':
                # For today, show payslips active in the current month
                month_start = today.replace(day=1)
                month_end = month_start + relativedelta(months=1, days=-1)
                payslip_domain += [('start_date', '<=', month_end), ('to_date', '>=', month_start)]
            elif date_filter == 'month':
                payslip_domain += [('start_date', '>=', start_date), ('to_date', '<=', end_date)]

            pending_payslips = self.env['employee.payslip'].search_read(
                payslip_domain,
                ['employee_id', 'payslip_name', 'start_date', 'to_date']
            )

            for payslip in pending_payslips:
                employee = self.browse(payslip['employee_id'][0])
                pending_payslips_list.append({
                    'id': payslip['id'],
                    'employee_id': payslip['employee_id'][0],
                    'employee_name': payslip['employee_id'][1],
                    'department': employee.department_id.name or 'N/A',
                    'name': payslip['payslip_name'],
                    'date_start': payslip['start_date'],
                    'date_end': payslip['to_date'],
                })

        # Ending Contracts
        ending_contracts_list = []
        if 'hr.contract' in self.env:
            contract_domain = [('state', '=', 'open'), ('date_end', '!=', False)]
            if date_filter == 'today':
                contract_domain += [('date_end', '=', today)]
            else:
                contract_domain += [('date_end', '>=', start_date), ('date_end', '<=', end_date)]

            ending_contracts = self.env['hr.contract'].search_read(
                contract_domain,
                ['employee_id', 'name', 'date_end']
            )
            for contract in ending_contracts:
                employee = self.browse(contract['employee_id'][0])
                ending_contracts_list.append({
                    'id': contract['id'],
                    'employee_id': contract['employee_id'][0],
                    'employee_name': contract['employee_id'][1],
                    'job_title': employee.job_id.name or 'N/A',
                    'name': contract['name'],
                    'date_end': contract['date_end'],
                })

        # Leaderboard Data (Commissions)
        leaderboard_data = []
        if 'commission.report' in self.env:
            # Report period overlaps the selected dashboard period
            # (works even when the plan period spans the whole window).
            commission_domain = [
                ('date_from', '<=', end_date),
                ('date_to', '>=', start_date),
                ('user_id', '!=', False),
            ]
            commission_reports = self.env['commission.report'].search_read(
                commission_domain,
                ['user_id', 'commission_amount', 'order_ids']
            )
            user_stats = {}
            for report in commission_reports:
                user = report['user_id']
                uid = user[0] if isinstance(user, (list, tuple)) else False
                if not uid:
                    continue
                if uid not in user_stats:
                    user_stats[uid] = {
                        'commission': 0.0,
                        'name': user[1] if isinstance(user, (list, tuple)) else '',
                        'deals': 0,
                    }
                user_stats[uid]['commission'] += report.get('commission_amount') or 0.0
                user_stats[uid]['deals'] += len(report.get('order_ids') or [])

            sorted_stats = sorted(user_stats.values(), key=lambda x: x['commission'], reverse=True)
            for uid, stat in zip(user_stats.keys(), sorted_stats):
                leaderboard_data.append({
                    'rank': sorted_stats.index(stat) + 1,
                    'user_id': uid,
                    'name': stat['name'],
                    'commission': stat['commission'],
                    'deals': stat['deals'],
                })

        # Recruitment Stages Data (Chart) - Affected by date filter
        recruitment_stages_labels = []
        recruitment_stages_counts = []
        if 'hr.recruitment.stage' in self.env and 'hr.applicant' in self.env:
            stages = self.env['hr.recruitment.stage'].search([], order='sequence asc')
            for stage in stages:
                count = self.env['hr.applicant'].search_count([
                    ('stage_id', '=', stage.id),
                    ('create_date', '>=', start_date),
                    ('create_date', '<=', end_date)
                ])
                if count > 0:
                    recruitment_stages_labels.append(stage.name)
                    recruitment_stages_counts.append(count)

        # Contract Type Data (Chart) - Not usually filtered by date, but by active status
        contract_type_labels = []
        contract_type_counts = []
        if 'hr.contract.type' in self.env and 'hr.contract' in self.env:
            types = self.env['hr.contract.type'].search([])
            for ctype in types:
                count = self.env['hr.contract'].search_count([
                    ('contract_type_id', '=', ctype.id),
                    ('state', '=', 'open')
                ])
                if count > 0:
                    contract_type_labels.append(ctype.name)
                    contract_type_counts.append(count)
            # Running contracts with no Contract Type set must still show up
            untyped_count = self.env['hr.contract'].search_count([
                ('contract_type_id', '=', False),
                ('state', '=', 'open')
            ])
            if untyped_count > 0:
                contract_type_labels.append('Unspecified')
                contract_type_counts.append(untyped_count)

        # Contract Status Data (Chart) - Not affected by date filter
        contract_status_labels = []
        contract_status_counts = []
        if 'hr.contract' in self.env:
            # Get all selection values for the 'state' field in hr.contract
            contract_states = dict(self.env['hr.contract']._fields['state'].selection)
            for state_key, state_label in contract_states.items():
                count = self.env['hr.contract'].search_count([('state', '=', state_key)])
                if count > 0:
                    contract_status_labels.append(state_label)
                    contract_status_counts.append(count)

        # Time Off and Allocations - Affected by date filter
        timeoff_records = []
        if 'hr.leave' in self.env:
            leave_domain = [('request_date_from', '>=', start_date), ('request_date_to', '<=', end_date)]
            leaves = self.env['hr.leave'].search_read(
                leave_domain,
                ['employee_id', 'holiday_status_id', 'request_date_from', 'request_date_to', 'number_of_days', 'state']
            )
            for leave in leaves:
                timeoff_records.append({
                    'id': leave['id'],
                    'employee_id': leave['employee_id'][0],
                    'employee_name': leave['employee_id'][1],
                    'leave_type': leave['holiday_status_id'][1],
                    'request_type': 'leave',
                    'date_from': leave['request_date_from'],
                    'date_to': leave['request_date_to'],
                    'days': leave['number_of_days'],
                    'state': leave['state'],
                })

        if 'hr.leave.allocation' in self.env:
            alloc_domain = [('date_from', '>=', start_date)] # Allocation dates are simpler
            allocations = self.env['hr.leave.allocation'].search_read(
                alloc_domain,
                ['employee_id', 'holiday_status_id', 'date_from', 'date_to', 'number_of_days_display', 'state']
            )
            for alloc in allocations:
                timeoff_records.append({
                    'id': alloc['id'],
                    'employee_id': alloc['employee_id'][0],
                    'employee_name': alloc['employee_id'][1],
                    'leave_type': alloc['holiday_status_id'][1],
                    'request_type': 'allocation',
                    'date_from': alloc['date_from'],
                    'date_to': alloc['date_to'],
                    'days': alloc['number_of_days_display'],
                    'state': alloc['state'],
                })

        # Upcoming Leaves for Card - Always from 'today' onwards
        upcoming_leaves = []
        if 'hr.leave' in self.env:
            upcoming_leaves_raw = self.env['hr.leave'].search_read(
                [('state', '=', 'validate'), ('request_date_from', '>=', today)],
                ['employee_id', 'holiday_status_id', 'request_date_from', 'request_date_to'],
                order='request_date_from asc'
            )
            for leave in upcoming_leaves_raw:
                d_from = leave['request_date_from']
                d_to = leave['request_date_to']
                date_str = d_from.strftime('%a') if d_from == d_to else f"{d_from.strftime('%a')}-{d_to.strftime('%a')}"
                upcoming_leaves.append({
                    'employee_name': leave['employee_id'][1],
                    'leave_type': leave['holiday_status_id'][1],
                    'date_range': f"({date_str})",
                })


        return {
            'total_employees': total_employees,
            'job_applied_count': job_applied_count,
            'start_date': start_date,
            'end_date': end_date,
            'attendance_rate': attendance_rate,
            'upcoming_timeoff_count': upcoming_timeoff_count,
            # Previous-period values + change % for the KPI delta badges
            'total_employees_compare': total_employees_compare,
            'total_employees_pct': total_employees_pct,
            'job_applied_compare': job_applied_compare,
            'job_applied_pct': job_applied_pct,
            'attendance_rate_compare': attendance_rate_compare,
            'attendance_rate_pct': attendance_rate_pct,
            'upcoming_timeoff_compare': upcoming_timeoff_compare,
            'upcoming_timeoff_pct': upcoming_timeoff_pct,
            'kpi_compare_label': kpi_compare_label,
            'employee_status_labels': employee_status_labels,
            'employee_status_counts': employee_status_counts,
            'attendance_trend_labels': attendance_trend_labels,
            'attendance_trend_data': attendance_trend_data,
            'pending_payslips': pending_payslips_list,
            'ending_contracts': ending_contracts_list,
            'leaderboard_data': leaderboard_data,
            'timeoff_records': timeoff_records,
            'upcoming_leaves': upcoming_leaves,
            'recruitment_stages_labels': recruitment_stages_labels,
            'recruitment_stages_counts': recruitment_stages_counts,
            'contract_type_labels': contract_type_labels,
            'contract_type_counts': contract_type_counts,
            'contract_status_labels': contract_status_labels,
            'contract_status_counts': contract_status_counts,
            'is_recruitment_installed': 'hr.applicant' in self.env,
        }

    def action_open_record(self):
        """
              Action to open an employee record in a new window.

              This method returns an action to open the employee record in a new window.
              It sets the appropriate model, resource ID, view ID, and target for the action.

              Returns:
                  dict: A dictionary describing the action to be executed.
              """
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.employee',
            'res_id': self.env.context.get('id', False),
            'view_id': self.env.ref('hr.view_employee_form').id,
            'target': 'new',
            'views': [(False, 'form')],
        }
