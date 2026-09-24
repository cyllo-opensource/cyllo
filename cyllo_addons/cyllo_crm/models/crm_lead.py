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
import logging
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytz
from dateutil.relativedelta import relativedelta
# todo: Getting location using AI is pending (change langchain)
# from langchain_core.messages import HumanMessage
# from langchain_google_genai import ChatGoogleGenerativeAI
from lxml import html
from markupsafe import Markup
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)


class CrmLead(models.Model):
    """Inherits the base crm.lead model and adds Tasks information in the lead form."""
    _inherit = 'crm.lead'

    lead_idle_days = fields.Integer(string="Idle days", help="Idle days")
    last_stage_update_date = fields.Datetime(string="stage change date",
                                             default=date.today())
    # Dashboard Fields
    is_dismissed_notification = fields.Boolean(
        string='Dismissed Notification',
        default=False,
        help="This field is used to indicate if"
             " the notification for this lead has"
             " been dismissed by the user."
    )
    is_marked_as_read = fields.Boolean(
        string='Marked as Read',
        default=False,
        help="This field is used to indicate if"
             " the notification for this lead has"
             " been marked as read by the user."
    )
    # Advance followup fields
    exit_criteria_activity_name = fields.Char()
    triggered_stage_ids = fields.Many2many('crm.stage',
                                           relation='crm_lead_stage_triggered_rel',
                                           column1='lead_id',
                                           column2='stage_id',
                                           string='Stages Triggered',
                                           readonly=True)
    ex_probability = fields.Float('Probability', copy=False,
                                  readonly=False, store=True)
    partner_work_status = fields.Html(
        string="Work Status",
        compute="_compute_partner_work_status",
    )

    partner_local_time = fields.Datetime(string="Partner Local Time")

    is_pinned = fields.Boolean(
        string='Pinned',
        default=False,
        help="Pin this message to the top of the chatter",
    )
    is_installed = fields.Boolean(
        string='Installed',
        default=False,
        compute='_compute_is_installed'
    )

    has_activities = fields.Boolean(
        string='Has Activities',
        compute='_compute_has_activities',
        store=True
    )

    @api.model
    def create(self, vals):
        """Override the Create function to create exit criteria activity if the stage have one"""
        # Create the lead record first
        lead = super(CrmLead, self).create(vals)
        stage = lead.stage_id
        # Check if the lead has a stage
        if stage:
            # Look for activities associated with this stage
            exit_criteria = self.env['crm.stage.activity'].search([
                ('stage_id', '=', stage.id)
            ], limit=1)
            if exit_criteria:
                lead.exit_criteria_activity_name = exit_criteria.activity_id.name
                # Optional print/debug
                _logger.info(
                    f"Exit Criteria for Lead {lead.id}: {lead.exit_criteria_activity_name}")
                self.env['crm.stage.activity']._create_exit_criteria_if_needed(
                    lead.id, stage.id)
        return lead

    def write(self, values):
        """Override write to prevent stage changes if exit criteria
        are not completed and create new exit criteria activity
        if the new stage have one"""
        if 'stage_id' in values:
            # Check if the stage is changing
            new_stage_id = values['stage_id']
            for record in self:
                if record.stage_id.id != new_stage_id:
                    if record.has_outstanding_exit_criteria():
                        raise ValidationError(
                            _("Cannot change stage. Please complete all mandatory activities first.")
                        )
                    exit_criteria = self.env['crm.stage.activity'].search([
                        ('stage_id', '=', new_stage_id)
                    ], limit=1)
                    record.exit_criteria_activity_name = exit_criteria.activity_id.name if exit_criteria else False
                    self.env[
                        'crm.stage.activity']._create_exit_criteria_if_needed(
                        record.id, new_stage_id
                    )

        # Partner working details - Pin message when partner_work_status is computed
        result = super(CrmLead, self).write(values)

        # Post pinned message after write completes successfully
        for record in self:
            if (
                    record.partner_id
                    and record.partner_id.partner_working_details
                    and not record.is_pinned
            ):
                msg = record._message_log(
                    body=Markup(record.partner_id.partner_working_details)
                )
                msg.write({'is_pinned': True})
                record.is_pinned = True

        return result

    # crm functions
    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        """Override to filter stages based on lead/opportunity type"""
        lead_type = self._context.get('default_type')
        if lead_type == 'lead':
            search_domain = [('type', 'in', ['lead', 'both']),
                             ('is_won', '=', False)]
        elif lead_type == 'opportunity':
            search_domain = [('type', 'in', ['opportunity', 'both'])]
        else:
            search_domain = [('type', 'in', ['lead', 'opportunity', 'both'])]

        stage_ids = stages._search(search_domain, order=order,
                                   access_rights_uid=self._uid)
        return stages.browse(stage_ids)

    @api.onchange('stage_id')
    def update_last_stage(self):
        """method to update last_stage_update field"""
        self.last_stage_update_date = date.today()

    def action_deal_reminder(self):
        """cron job for reminding sales persons for the idle leads for more than specified in the settings,deal reminder field"""
        config_param = self.env['ir.config_parameter'].sudo()
        if not config_param.get_param('Cyllo_Crm.deal_reminder'):
            return

        reminder_days = config_param.get_param('Cyllo_Crm.deal_reminder_days')
        reminder_days = int(reminder_days) if reminder_days else 0

        today = date.today()
        cutoff_date = today - timedelta(days=reminder_days)
        cutoff_datetime = datetime.combine(cutoff_date, datetime.min.time())
        leads = self.env['crm.lead'].search([
            ('stage_id.is_won', '!=', True),
            ('company_id', '!=', False),
            ('last_stage_update_date', '<',
             fields.Datetime.to_string(cutoff_datetime)),
        ])
        if not leads:
            return

        template = self.env.ref('cyllo_crm.deal_reminder')
        for rec in leads:
            days_difference = (
                    today - rec.last_stage_update_date.date()).days
            rec.lead_idle_days = days_difference - reminder_days
            template.send_mail(rec.id, force_send=True)

    @api.model
    def retrieve_crm_dashboard(self):
        """ This function returns the values to populate the custom dashboard in
            the crm lead along with filter domains for each category"""
        result = {
            'my_leads': 0,
            'my_opportunities': 0,
            'no_activity': 0,
            'no_activity_o': 0,
            'idle': 0,
            'idle_o': 0,
            'overdue': 0,
            'overdue_o': 0,
            'due_today': 0,
            'due_today_o': 0,
            'my_activity': 0,
            'my_activity_o': 0,
            'can_see_all_leads': self.env.user.has_group('sales_team.group_sale_salesman_all_leads'),
        }
        crm_lead = self.env['crm.lead']
        current_date = fields.Date.today()

        # Base domain for leads
        base_domain = [('type', '=', 'lead')]
        base_domain_o = [('type', '=', 'opportunity')]

        # Total active leads
        result['my_leads'] = crm_lead.search_count(
            [('type', '=', 'lead'), ('user_id', '=', self.env.user.id)])
        result['my_opportunities'] = crm_lead.search_count(
            [('user_id', '=', self.env.user.id)])

        # No activity leads
        no_activity_domain = base_domain + [('activity_ids', '=', False),
                                            ('user_id', '=', self.env.user.id)]
        result['no_activity'] = crm_lead.search_count(no_activity_domain)
        no_activity_domain_o = base_domain_o + [('activity_ids', '=', False)]
        result['no_activity_o'] = crm_lead.search_count(no_activity_domain_o)

        # Idle leads (no activity for last 7 days)
        seven_days_ago = fields.Date.add(current_date, days=-7)
        idle_domain = base_domain + [
            ('activity_user_id', '=', self.env.user.id),
            ('activity_ids.date_deadline', '<', seven_days_ago),
            ('activity_ids.state', '!=', 'done')
        ]
        result['idle'] = crm_lead.search_count(idle_domain)
        idle_domain_o = base_domain_o + [
            ('activity_ids.date_deadline', '<', seven_days_ago),
            ('activity_ids.state', '!=', 'done')
        ]
        result['idle_o'] = crm_lead.search_count(idle_domain_o)

        # Overdue activities
        overdue_domain = base_domain + [
            ('activity_ids.date_deadline', '<', current_date),
            ('activity_ids.state', '!=', 'done')
        ]
        result['overdue'] = crm_lead.search_count(overdue_domain)
        overdue_domain_o = base_domain_o + [
            ('activity_ids.date_deadline', '<', current_date),
            ('activity_ids.state', '!=', 'done')
        ]
        result['overdue_o'] = crm_lead.search_count(overdue_domain_o)

        # Due today
        due_today_domain = base_domain + [
            ('activity_ids.date_deadline', '=', current_date),
            ('activity_ids.state', '!=', 'done')
        ]
        result['due_today'] = crm_lead.search_count(due_today_domain)
        due_today_domain_o = base_domain_o + [
            ('activity_ids.date_deadline', '=', current_date),
            ('activity_ids.state', '!=', 'done')
        ]
        result['due_today_o'] = crm_lead.search_count(due_today_domain_o)

        # Activities today
        activity_today_domain = base_domain + [
            ('activity_ids.date_deadline', '>', current_date),
            ('activity_ids.state', '!=', 'done')
        ]
        result['activity_today'] = crm_lead.search_count(activity_today_domain)
        activity_today_domain_o = base_domain_o + [
            ('activity_ids.date_deadline', '>', current_date),
            ('activity_ids.state', '!=', 'done')
        ]
        result['activity_today_o'] = crm_lead.search_count(
            activity_today_domain_o)

        # ---------- All Leads row (global — not restricted to current user) ----------
        result['all_leads'] = crm_lead.search_count(base_domain)

        all_no_activity_domain = base_domain + [('activity_ids', '=', False)]
        result['all_no_activity'] = crm_lead.search_count(all_no_activity_domain)

        all_idle_domain = base_domain + [
            ('activity_ids.date_deadline', '<', seven_days_ago),
            ('activity_ids.state', '!=', 'done')
        ]
        result['all_idle'] = crm_lead.search_count(all_idle_domain)

        all_overdue_domain = base_domain + [
            ('activity_ids.date_deadline', '<', current_date),
            ('activity_ids.state', '!=', 'done')
        ]
        result['all_overdue'] = crm_lead.search_count(all_overdue_domain)

        all_due_today_domain = base_domain + [
            ('activity_ids.date_deadline', '=', current_date),
            ('activity_ids.state', '!=', 'done')
        ]
        result['all_due_today'] = crm_lead.search_count(all_due_today_domain)

        all_activity_today_domain = base_domain + [
            ('activity_ids.date_deadline', '>', current_date),
            ('activity_ids.state', '!=', 'done')
        ]
        result['all_activity_today'] = crm_lead.search_count(all_activity_today_domain)

        return result

    #   Dashboard functions
    @api.model
    def get_dashboard_data(self, domain=None, daterange=None):
        """
        Get comprehensive dashboard data for CRM
        """
        domain = list(domain or [])
        if self.env.user.has_group('sales_team.group_sale_salesman'):
            user_domain = [('user_id', '=', self.env.uid)]
            if user_domain not in domain:
                domain.extend(user_domain)

        # Get metrics data
        metrics = self._get_metrics_data(domain, daterange)

        # Get revenue trend data (last 6 months)
        revenue_trend = self._get_revenue_trend_data(domain)

        # Get pipeline data
        pipeline = self._get_pipeline_data(domain)

        # Get activities data for the domain date range
        activities = self._get_activities_data(domain)

        # Get top performers
        top_performers = self._get_top_performers_data(domain)

        dashboard_data = {
            'metrics': metrics,
            'revenue_trend': revenue_trend,
            'pipeline': pipeline,
            'activities': activities,
            'top_performers': top_performers,
        }

        return dashboard_data

    @api.model
    def get_dashboard_user_context(self):
        """Return dashboard visibility defaults for the current user."""
        team = self.env['crm.team'].search(
            [('member_ids', 'in', [self.env.uid])],
            limit=1,
        )
        return {
            'current_user_id': self.env.uid,
            'current_team_id': team.id if team else False,
            'hide_salesperson_filter': (
                self.env.user.has_group('sales_team.group_sale_salesman')
                and not (self.env.user.has_group('sales_team.group_sale_manager')
                or self.env.user.has_group('sales_team.group_sale_salesman_all_leads'))
            ),
        }

    def _get_company_currency_sale_revenue(self, leads):
        """Return confirmed sales revenue converted to current company currency."""
        company_id = self.env.company
        revenue = 0
        label = "Total Revenue"
        if 'order_ids' in self.env['crm.lead']._fields:
            sale_orders = leads.order_ids.filtered(
                lambda order: order.state == 'sale') if leads else []
            for order_id in sale_orders:
                revenue += order_id.currency_id._convert(
                    order_id.amount_total,
                    company_id.currency_id,
                    company_id,
                    fields.Date.to_date(order_id.date_order),
                )
        else:
            revenue = sum(leads.mapped('expected_revenue')) if leads else 0
            label = "Total Expected Revenue"
        return revenue, label

    def _get_metrics_data(self, domain=None, daterange=None):
        """Calculate key metrics with month-over-month comparison"""
        start_date = next(
            (d[2].split(' ')[0] for d in domain if d[1] == '>='), None)
        team_id = next(
            (d[2] for d in domain if d[0] == 'team_id'), None)
        user_id = next(
            (d[2] for d in domain if d[0] == 'user_id'), None)

        # Convert the strings to dates and set them as the start and end dates
        start_date = datetime.strptime(start_date,
                                       "%Y-%m-%d").date() + timedelta(days=1)
        prev_start_date = datetime.now().date()
        prev_end_date = datetime.now().date()
        if daterange == 'this_month':
            prev_start_date = start_date - relativedelta(months=1)
            prev_end_date = start_date - relativedelta(days=1)
        elif daterange == 'this_year':
            prev_start_date = start_date - relativedelta(years=1)
            prev_end_date = start_date - relativedelta(days=1)
        elif daterange == 'this_week':
            prev_start_date = start_date - relativedelta(weeks=1)
            prev_end_date = start_date - relativedelta(days=1)
        elif daterange == 'this_quarter':
            prev_start_date = start_date - relativedelta(months=3)
            prev_end_date = start_date - relativedelta(days=1)
        elif daterange == 'today':
            yesterday = start_date - timedelta(days=1)
            prev_start_date = yesterday
            prev_end_date = yesterday

        current_leads = self.search(domain)
        prev_leads = []
        if prev_start_date != datetime.now().date() and prev_end_date != datetime.now().date():
            prev_leads_domain = [
                ('date_closed', '>=', prev_start_date),
                ('date_closed', '<=', prev_end_date),
            ]
            if team_id:
                prev_leads_domain.append(('team_id', '=', team_id))
            if user_id:
                prev_leads_domain.append(('user_id', '=', user_id))
            prev_leads = self.search(prev_leads_domain)

        current_won_leads = current_leads.filtered(
            lambda r: r.stage_id.is_won) if current_leads else []
        previous_won_leads = prev_leads.filtered(
            lambda r: r.stage_id.is_won) if prev_leads else []
        current_active_leads = current_leads.filtered(
            lambda r: not r.stage_id.is_won) if current_leads else []
        previous_active_leads = prev_leads.filtered(
            lambda r: not r.stage_id.is_won) if prev_leads else []

        # Calculate metrics
        current_revenue, label = self._get_company_currency_sale_revenue(
            current_won_leads)
        last_month_revenue, label = self._get_company_currency_sale_revenue(
            previous_won_leads)

        active_leads_count = len(current_active_leads)
        last_month_active_leads = len(previous_active_leads)

        current_conversion_rate = (len(current_won_leads) / len(
            current_leads) * 100) if current_leads else 0
        last_month_conversion_rate = (
                len(previous_won_leads) / len(
            previous_active_leads) * 100) if previous_active_leads else 0

        deals_closed_count = len(current_won_leads)
        last_month_deals_closed = len(previous_won_leads)

        # Calculate percentage changes
        revenue_change = self._calculate_percentage_change(current_revenue,
                                                           last_month_revenue)
        leads_change = self._calculate_percentage_change(active_leads_count,
                                                         last_month_active_leads)
        conversion_change = current_conversion_rate - last_month_conversion_rate
        deals_change = self._calculate_percentage_change(deals_closed_count,
                                                         last_month_deals_closed)

        return {
            'total_revenue': {
                'value': current_revenue,
                'label': label,
                'change': revenue_change
            },
            'active_leads': {
                'value': active_leads_count,
                'change': leads_change,
                'records': current_active_leads.ids if current_active_leads else []
            },
            'conversion_rate': {
                'value': round(current_conversion_rate, 1),
                'change': round(conversion_change, 1)
            },
            'deals_closed': {
                'value': deals_closed_count,
                'change': deals_change,
                'records': current_won_leads.ids if current_won_leads else []
            }
        }

    def _get_revenue_trend_data(self, domain=None):
        """Get revenue and leads trend for the last 6 months"""
        data = []
        today = datetime.now().date()

        for i in range(5, -1, -1):  # Last 6 months
            month_start = (today.replace(day=1) - relativedelta(months=i))
            month_end = (month_start + relativedelta(months=1) - timedelta(
                days=1))

            # Build domains for revenue
            won_leads_domain = [
                ('stage_id.is_won', '=', True),
                ('date_closed', '>=', month_start),
                ('date_closed', '<=', month_end)
            ]

            # Build domains for leads created
            leads_created_domain = [
                ('create_date', '>=', month_start),
                ('create_date', '<=', month_end)
            ]

            # Add custom domain if provided
            if domain:
                won_leads_domain.extend(domain)
                leads_created_domain.extend(domain)

            # Get revenue for the month
            won_leads = self.search(won_leads_domain)

            # Get leads created in the month
            leads_created = self.search(leads_created_domain)

            revenue = sum(won_leads.mapped('order_ids.amount_total') or [
                0]) if 'order_ids' in won_leads._fields else 0
            leads_count = len(leads_created)

            data.append({
                'month': month_start.strftime('%b'),
                'revenue': revenue,
                'leads': leads_count
            })

        return data

    def _get_pipeline_data(self, domain=None):
        """Get pipeline distribution by stages"""
        stages = self.env['crm.stage'].search([])

        # Build domain for total leads
        total_leads_domain = [('active', '=', True)]
        if domain:
            total_leads_domain.extend(domain)

        total_leads = len(self.search(total_leads_domain))

        if total_leads == 0:
            return []

        pipeline_data = []
        colors = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6',
                  '#06B6D4']

        for i, stage in enumerate(stages):
            # Build domain for leads in this stage
            stage_domain = [
                ('stage_id', '=', stage.id),
                ('active', '=', True)
            ]
            if domain:
                stage_domain.extend(domain)

            leads_in_stage = len(self.search(stage_domain))
            percentage = round((leads_in_stage / total_leads) * 100, 1)

            if percentage > 0:  # Only include stages with leads
                pipeline_data.append({
                    'stage': stage.name,
                    'value': percentage,
                    'color': colors[i % len(colors)]
                })

        return pipeline_data

    def _get_activities_data(self, domain=None):
        """Get activities data from leads which deadline is within the date range from domain"""
        activity_data = []
        # Get the start and end dates from the domain as strings
        start_date = next(
            (d[2].split(' ')[0] for d in domain if d[1] == '>='), None)
        end_date = next(
            (d[2].split(' ')[0] for d in domain if d[1] == '<='), None)

        # Convert the strings to dates and set them as the start and end dates
        start_date = datetime.strptime(start_date,
                                       "%Y-%m-%d").date() + timedelta(days=1)
        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
        lead_ids = self.search(domain).mapped("id")
        activities = self.env['mail.activity'].search(
            [('res_model', '=', 'crm.lead'), ('res_id', 'in', lead_ids),
             ('date_deadline', '>=', start_date),
             ('date_deadline', '<=', end_date)])

        for act in activities:
            activity_data.append({
                'name': act.activity_type_id.name,
                'date_deadline': str(act.date_deadline),
                'user_name': act.user_id.name,
            })
        return activity_data

    def _get_top_performers_data(self, domain=None):
        """Get top-performing sales people for domain"""
        # Get all sales people with deals
        salespeople = self.env['res.users'].search([
            ('groups_id', 'in',
             self.env.ref('sales_team.group_sale_salesman').ids)
        ])
        start_date = next(
            (d[2] for d in domain if d[1] == '>='), None)
        end_date = next(
            (d[2] for d in domain if d[1] == '<='), None)

        performers = []
        for user in salespeople:
            # Build domain for won deals
            won_deals_domain = [
                ('user_id', '=', user.id),
                ('stage_id.is_won', '=', True),
                ('date_closed', '>=', start_date),
                ('date_closed', '<=', end_date)
            ]

            # Add a custom domain if provided
            if domain:
                won_deals_domain.extend(domain)

            # Get won deals
            won_deals = self.search(won_deals_domain)

            if won_deals:
                total_amount = sum(won_deals.mapped('expected_revenue') or [0])
                deals_count = len(won_deals)

                performers.append({
                    'name': user.name,
                    'deals': deals_count,
                    'amount': total_amount
                })

        # Sort by amount and return top 4
        performers.sort(key=lambda x: x['amount'], reverse=True)
        return performers[:4]

    def _calculate_percentage_change(self, current, previous):
        """Calculate percentage change between two values"""
        if previous == 0:
            return 100 if current > 0 else 0
        return round(((current - previous) / previous) * 100, 1)

    @api.model
    def dismiss_notification(self, lead_ids):
        """Dismiss lead notifications"""
        leads = self.browse(lead_ids)
        leads.write({'is_dismissed_notification': True})
        for lead in leads:
            lead.is_dismissed_notification = True

            # Also update related activities
            activities = self.env['mail.activity'].search([
                ('res_model', '=', 'crm.lead'),
                ('res_id', '=', lead.id)
            ])

            activities.write({'is_dismissed_notification': True})

        return True

    @api.model
    def mark_as_read(self, lead_ids):
        """Mark lead notifications as read"""
        leads = self.browse(lead_ids).sudo()
        leads.write({'is_marked_as_read': True})
        for lead in leads:
            lead.is_marked_as_read = True

            # Also update related activities
            activities = self.env['mail.activity'].search([
                ('res_model', '=', 'crm.lead'),
                ('res_id', '=', lead.id)
            ])

            activities.write({'is_marked_as_read': True})

        return {
            'updated': len(leads),
            'sample_result': {lead.id: lead.is_marked_as_read for lead in
                              leads[:5]}
        }

    @api.model
    def get_notifications(self):
        """Get lead notifications for dashboard"""
        notifications = []
        current_date = fields.Date.today()
        recent_date = fields.Datetime.now() - timedelta(days=7)
        try:
            # New leads
            new_leads = self.search([
                ('create_date', '>=', recent_date),
                ('type', '=', 'lead'),
                ('is_dismissed_notification', '=', False),
            ], order='create_date desc', limit=10)
            notifications.extend([
                self.build_notifications('new_lead', lead, 'New Lead Created',
                                         f'New lead "{lead.name}" has been created',
                                         'new_lead', 'normal')
                for lead in new_leads
            ])

            overdue_activities = self.env['mail.activity'].search([
                ('res_model', '=', 'crm.lead'),
                ('date_deadline', '<=', current_date),
                ('is_dismissed_notification', '=', False),
                ('user_id', '=', self.env.user.id)
            ], limit=5)

            # Batch leads for activities
            leads_by_id = {lead.id: lead for lead in
                           self.browse(overdue_activities.mapped('res_id'))}
            for act in overdue_activities:
                lead = leads_by_id.get(act.res_id)
                if not lead:
                    continue

                is_today = act.date_deadline == current_date
                title = 'Activity Due Today' if is_today else 'Activity Overdue'
                base_msg = f'Activity "{act.summary or act.activity_type_id.name}"'
                message = (
                    f'Mandatory {base_msg} is overdue' if act.is_exit_criteria
                    else f'{base_msg} is {"due today" if is_today else "overdue"}')
                priority = 'high' if act.is_exit_criteria else (
                    'normal' if is_today else 'medium')

                notifications.append(self.build_notifications(
                    'today_activity' if is_today else 'overdue_activity',
                    lead, title, message, 'activity_due', priority
                ))

            avg_revenue = self.search_read(
                [('expected_revenue', '>', 0)],
                ['expected_revenue']
            )

            if avg_revenue:
                avg_val = sum(l['expected_revenue'] for l in avg_revenue) / len(
                    avg_revenue)
                high_value_leads = self.search([
                    ('create_date', '>=', recent_date),
                    ('expected_revenue', '>', avg_val),
                    ('is_dismissed_notification', '=', False),
                ], limit=3)

                notifications.extend([
                    self.build_notifications('high_value', lead,
                                             'High Value Lead',
                                             f'High value lead "{lead.name}" created',
                                             'new_lead', 'high')
                    for lead in high_value_leads
                ])

            # Final sorting & limiting
            return sorted(notifications, key=lambda x: x['create_date'],
                          reverse=True)[:20]


        except Exception as e:
            # Log error and return empty list
            import logging
            _logger = logging.getLogger(__name__)
            _logger.error(f"Error getting notifications: {str(e)}")
            return []

    def build_notifications(self, prefix, rec, title, message, ntype, priority):
        """Create notifications as per the datas passed from get_notification function"""
        return {
            'id': f"{prefix}{rec.id}",
            'title': title,
            'message': message,
            'type': ntype,
            'priority': priority,
            'is_read': getattr(rec, 'is_marked_as_read', False),
            'create_date': rec.create_date.isoformat(),
            'lead_id': getattr(rec, 'id', None),
            'lead_name': getattr(rec, 'name', ''),
            'lead_company': getattr(rec, 'partner_name', '') or '',
            'lead_stage': rec.stage_id.name if getattr(rec, 'stage_id',
                                                       False) else 'New',
            'lead_expected_revenue': f"${rec.expected_revenue:,.0f}" if rec.expected_revenue else ''
        }

    # Advance followup constrain
    def has_outstanding_exit_criteria(self):
        """Check if lead has any outstanding exit criteria activities"""
        self.ensure_one()
        exit_criteria_activities = self.env['mail.activity'].search_count([
            ('res_model', '=', 'crm.lead'),
            ('res_id', '=', self.id),
            ('is_exit_criteria', '=', True)
        ])
        return exit_criteria_activities > 0

    # todo: Getting location using AI is pending (change langchain)
    # def action_get_customer_local_time(self):
    #     """
    #     Function for getting partner time and current time using Google Gemini API.
    #     Automatically pins the working hours table in the chatter.
    #     """
    #     # Check if already fetched
    #     if self.partner_work_status:
    #         return {
    #             'type': 'ir.actions.client',
    #             'tag': 'display_notification',
    #             'params': {
    #                 'title': "Customer Current Time",
    #                 'message': "Working hours already fetched!",
    #                 'type': 'info',
    #                 'sticky': False,
    #             }
    #         }
    #
    #     API_KEY = request.env[
    #         'ir.config_parameter'
    #     ].sudo().get_param('cyllo_agent.api_key')
    #     model_id = self.env['ir.config_parameter'].sudo().get_param(
    #         'agent.llm_model_id'
    #     )
    #
    #     if not model_id:
    #         return {
    #             'type': 'ir.actions.client',
    #             'tag': 'display_notification',
    #             'params': {
    #                 'title': "Configuration Error",
    #                 'message': "LLM Model ID is not configured. Please set it in settings.",
    #                 'type': 'danger',
    #                 'sticky': False,
    #             }
    #         }
    #
    #     llm_model = self.env['cyllo.llm'].sudo().browse(int(model_id))
    #     model_name = llm_model.name
    #
    #     if not API_KEY:
    #         return {
    #             'type': 'ir.actions.client',
    #             'tag': 'display_notification',
    #             'params': {
    #                 'title': "Missing API Key",
    #                 'message': "API Key is missing. Please configure it before proceeding.",
    #                 'type': 'danger',
    #                 'sticky': False,
    #             }
    #         }
    #
    #     llm = ChatGoogleGenerativeAI(
    #         model=model_name,
    #         google_api_key=API_KEY
    #     )
    #
    #     message = HumanMessage(
    #         content=[
    #             {
    #                 "type": "text",
    #                 "text": (
    #                     f"Search Google and provide the official working hours of "
    #                     f"{self.partner_id.name} ({self.state_id.name}, {self.country_id.name}). "
    #                     f"First, show today's working shift in HH:MM to HH:MM format. "
    #                     f"Then show the IANA timezone (e.g., Asia/Kolkata, America/Los_Angeles, Europe/London). "
    #                     f"IMPORTANT: Only provide the IANA timezone name without any prefix or additional text. "
    #                     f"Then list the working hours for each weekday in HH:MM to HH:MM format. "
    #                     f"Do not add extra text, explanations, headings, or formatting. "
    #                     f"Format example:\n"
    #                     f"09:00 to 17:00\n"
    #                     f"Asia/Kolkata\n"
    #                     f"Monday: 09:00 to 17:00\n"
    #                     f"Tuesday: 09:00 to 17:00\n"
    #                     f"If the company cannot be found or no official working hours are available, "
    #                     f"output exactly: 'Sorry, company is not found'."
    #                 )
    #             }
    #         ]
    #     )
    #
    #     try:
    #         response = llm.invoke([message])
    #         data = response.content.split('\n')
    #
    #         if len(data) > 1 and 'Sorry, company is not found' not in response.content:
    #             # Save values
    #             self.partner_id.partner_working_hours = data[0]
    #
    #             # Clean timezone string
    #             timezone_str = data[1].strip()
    #
    #             # Remove common prefixes if present
    #             if timezone_str.lower().startswith('time zone:'):
    #                 timezone_str = timezone_str.split(':', 1)[1].strip()
    #             elif timezone_str.lower().startswith('timezone:'):
    #                 timezone_str = timezone_str.split(':', 1)[1].strip()
    #
    #             # Map common abbreviations to IANA format
    #             timezone_mapping = {
    #                 'IST': 'Asia/Kolkata',
    #                 'IST (UTC+5:30)': 'Asia/Kolkata',
    #                 'PST': 'America/Los_Angeles',
    #                 'EST': 'America/New_York',
    #                 'CST': 'America/Chicago',
    #                 'MST': 'America/Denver',
    #                 'GMT': 'Europe/London',
    #                 'CET': 'Europe/Paris',
    #                 'JST': 'Asia/Tokyo',
    #                 'AEST': 'Australia/Sydney',
    #             }
    #
    #             # Check if we need to map the timezone
    #             for abbr, iana_tz in timezone_mapping.items():
    #                 if timezone_str.upper().startswith(abbr):
    #                     timezone_str = iana_tz
    #                     break
    #
    #             self.partner_id.partner_time_zone = timezone_str
    #
    #             # Days of week
    #             days = [
    #                 "Monday", "Tuesday", "Wednesday",
    #                 "Thursday", "Friday", "Saturday", "Sunday"
    #             ]
    #
    #             # Build HTML table
    #             table_html = """
    #             <table style="border-collapse: collapse; width: 100%; margin: 10px 0;">
    #                 <thead>
    #                     <tr style="background-color: #f0f0f0;">
    #                         <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Information</th>
    #                         <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Details</th>
    #                     </tr>
    #                 </thead>
    #                 <tbody>
    #             """
    #
    #             # ---- Time Zone Row ----
    #             table_html += f"""
    #                 <tr style="background-color: #ffffff;">
    #                     <td style="border: 1px solid #ddd; padding: 8px;">
    #                         <strong>Time Zone</strong>
    #                     </td>
    #                     <td style="border: 1px solid #ddd; padding: 8px;">
    #                         {timezone_str}
    #                     </td>
    #                 </tr>
    #             """
    #
    #             # ---- Working Hours Rows ----
    #             for i, day in enumerate(days):
    #                 if i + 2 >= len(data):
    #                     break
    #
    #                 value = data[i + 2]
    #
    #                 # Remove "Monday:" from "Monday: 09:00 to 17:00"
    #                 if ':' in value:
    #                     day_label, value = value.split(':', 1)
    #                     value = value.strip()
    #
    #                 # Alternating row background
    #                 bg_color = "#f9f9f9" if i % 2 else "#ffffff"
    #
    #                 # Make value text red if closed
    #                 value_style = "color: red;" if value in ["00:00 to 00:00",
    #                                                          "Closed"] else ""
    #
    #                 table_html += f"""
    #                     <tr style="background-color: {bg_color};">
    #                         <td style="border: 1px solid #ddd; padding: 8px;">
    #                             <strong>{day}</strong>
    #                         </td>
    #                         <td style="border: 1px solid #ddd; padding: 8px; {value_style}">
    #                             {value}
    #                         </td>
    #                     </tr>
    #                 """
    #
    #             table_html += """
    #                 </tbody>
    #             </table>
    #             """
    #
    #             # Save to partner
    #             self.partner_id.write({
    #                 'partner_working_details': table_html
    #             })
    #
    #             # Trigger the write method which will create and pin the message
    #             self.write({})
    #
    #             return {
    #                 'type': 'ir.actions.client',
    #                 'tag': 'display_notification',
    #                 'params': {
    #                     'title': "Success!",
    #                     'message': "Working hours fetched and pinned to chatter successfully!",
    #                     'type': 'success',
    #                     'sticky': False,
    #                     'next': {
    #                         'type': 'ir.actions.client',
    #                         'tag': 'reload',
    #                     }
    #                 }
    #             }
    #
    #         return {
    #             'type': 'ir.actions.client',
    #             'tag': 'display_notification',
    #             'params': {
    #                 'title': "Not Found",
    #                 'message': "Company not found while fetching working hours",
    #                 'type': 'warning',
    #                 'sticky': False,
    #             }
    #         }
    #
    #     except Exception as e:
    #         _logger.error(f"Error during Gemini invocation: {e}")
    #         return {
    #             'type': 'ir.actions.client',
    #             'tag': 'display_notification',
    #             'params': {
    #                 'title': "Error",
    #                 'message': f"An error occurred: {str(e)}",
    #                 'type': 'danger',
    #                 'sticky': False,
    #             }
    #         }

    def _compute_partner_work_status(self):
        """Compute Partner Work Status using day-wise working hours"""
        for record in self:
            if not record.partner_id or not record.partner_id.partner_time_zone:
                record.partner_local_time = False
                record.partner_work_status = False
                continue

            try:
                # Clean and normalize timezone string
                timezone_str = record.partner_id.partner_time_zone.strip()

                # Remove common prefixes like "Time zone: " or "Timezone: "
                if timezone_str.lower().startswith('time zone:'):
                    timezone_str = timezone_str.split(':', 1)[1].strip()
                elif timezone_str.lower().startswith('timezone:'):
                    timezone_str = timezone_str.split(':', 1)[1].strip()

                # Map common timezone abbreviations to proper IANA timezone names
                timezone_mapping = {
                    'IST': 'Asia/Kolkata',
                    'IST (UTC+5:30)': 'Asia/Kolkata',
                    'PST': 'America/Los_Angeles',
                    'EST': 'America/New_York',
                    'CST': 'America/Chicago',
                    'MST': 'America/Denver',
                    'GMT': 'Europe/London',
                    'CET': 'Europe/Paris',
                    'JST': 'Asia/Tokyo',
                    'AEST': 'Australia/Sydney',
                    'NZST': 'Pacific/Auckland',
                }

                # Check if it's a known abbreviation
                for abbr, iana_tz in timezone_mapping.items():
                    if timezone_str.upper().startswith(abbr):
                        timezone_str = iana_tz
                        break

                # Try to create ZoneInfo object
                partner_time = datetime.now(ZoneInfo(timezone_str))

            except Exception as e:
                _logger.warning(
                    f"Invalid timezone '{record.partner_id.partner_time_zone}' for partner {record.partner_id.name}. "
                    f"Error: {e}. Using UTC as fallback."
                )
                # Fallback to UTC if timezone is invalid
                partner_time = datetime.now(ZoneInfo('UTC'))

            record.partner_local_time = partner_time.astimezone(
                pytz.UTC
            ).replace(tzinfo=None)

            parsed_data = record._parse_working_details(
                record.partner_id.partner_working_details
            )

            today = partner_time.strftime('%A')
            current_time = partner_time.time()

            # No working hours defined
            if today not in parsed_data:
                status = "Closed"
                color = "gray"
            else:
                today_hours = parsed_data[today]

                if today_hours.lower() == 'closed':
                    status = "Closed"
                    color = "red"
                else:
                    try:
                        end_time_str = today_hours.split(' to ')[-1]
                        end_time = datetime.strptime(
                            end_time_str, "%H:%M"
                        ).time()

                        status = "Open" if current_time < end_time else "Closed"
                        color = "green" if status == "Open" else "red"

                    except Exception:
                        status = "Closed"
                        color = "gray"

            record.partner_work_status = f"""
                <h5>
                    <span style="color: {color}; font-weight: bold;">
                        {status} : Current Time {partner_time.strftime("%H:%M")}
                    </span>
                </h5>
            """

            _logger.info(
                f"Partner local time: {record.partner_local_time}, "
                f"Day: {today}, Status: {status}"
            )

    def _parse_working_details(self, html_content):
        """Parse partner working details HTML into day-wise dict"""
        result = {}

        if not html_content:
            return result

        tree = html.fromstring(html_content)
        rows = tree.xpath('//tbody/tr')

        for row in rows:
            tds = row.xpath('./td')
            if len(tds) != 2:
                continue

            label = tds[0].xpath('string(.)').strip()
            value = tds[1].xpath('string(.)').strip()

            # Skip Time Zone row
            if label.lower() == 'time zone':
                continue

            result[label] = value

        return result

    def _compute_is_installed(self):
        """Function for checking is installed automation"""
        is_installed = self.env['ir.module.module'].search([
            ('name', '=', 'base_automation'),
            ('state', '=', 'installed')
        ], limit=1)
        if is_installed:
            self.is_installed = True
        else:
            self.is_installed = False

    def action_open_activity_graph(self):
        """Open activity graph for the current lead"""
        self.ensure_one()
        return {
            'name': 'Lead Activities Analysis',
            'type': 'ir.actions.act_window',
            'res_model': 'mail.activity',
            'view_mode': 'graph',
            'target': 'new',
            'domain': [
                ('res_model', '=', 'crm.lead'),
                ('res_id', '=', self.id),
            ],
            'context': {
                'group_by': 'activity_type_id',
                'graph_mode': 'pie',
            }
        }

    @api.depends('activity_ids')
    def _compute_has_activities(self):
        """compute activity ids for setting the visibility of button"""
        for lead in self:
            lead.has_activities = bool(lead.activity_ids)
