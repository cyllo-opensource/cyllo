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

    # ------------------------------------------------------------------
    # Raw-SQL helpers for the dashboard (query-based fast data fetching)
    # ------------------------------------------------------------------

    def _dashboard_where_from_domain(self, domain, alias="l"):
        """Translate the (simple, JS-built) dashboard domain into a SQL
        WHERE fragment + params. Only the leaves the dashboard can emit
        are supported:
            ('create_date', '>=', ts) / ('create_date', '<=', ts)
            ('date_closed', '>=', d) / ('date_closed', '<=', d)
            ('team_id', 'in', [ids])
            ('user_id', 'in', [ids]) / ('user_id', '=', id)
        """
        conditions = ["TRUE"]
        params = []
        for leaf in (domain or []):
            if not (isinstance(leaf, (list, tuple)) and len(leaf) == 3):
                raise ValueError(
                    f"Unsupported dashboard domain leaf: {leaf!r}")
            field, operator, value = leaf
            if field not in ("create_date", "date_closed", "team_id",
                             "user_id"):
                raise ValueError(
                    f"Unsupported dashboard domain field: {field!r}")
            if operator not in ("=", ">=", "<=", "in"):
                raise ValueError(
                    f"Unsupported dashboard domain operator: {operator!r}")
            column = f"{alias}.{field}"
            if operator == "in":
                conditions.append(f"{column} = ANY(%s)")
                params.append(list(value))
            else:
                conditions.append(f"{column} {operator} %s")
                params.append(value)
        return " AND ".join(conditions), params

    def _dashboard_access_conditions(self, alias="l"):
        """SQL equivalent of the crm.lead record rules applied by the ORM:
        - global multi-company rule (company_id in allowed companies + null)
        - 'Personal Leads' group rule for plain salesmen (own + unassigned)
        """
        conditions = [f"({alias}.company_id IS NULL OR "
                      f"{alias}.company_id = ANY(%s))"]
        params = [self.env.companies.ids]
        if self.env.user.has_group(
                "sales_team.group_sale_salesman") and not self.env.user.has_group(
                "sales_team.group_sale_salesman_all_leads"):
            conditions.append(f"({alias}.user_id = %s OR "
                              f"{alias}.user_id IS NULL)")
            params.append(self.env.uid)
        return " AND ".join(conditions), params

    def _dashboard_won_active_ids(self, where_sql, where_params, won=True):
        """Fetch lead ids for one won/active bucket in a single light query.
        Ordered like the model _order so id lists keep the same order the
        ORM search produced."""
        won_test = "TRUE" if won else "FALSE"
        self.env.cr.execute(
            f"""
            SELECT l.id
            FROM crm_lead l
            LEFT JOIN crm_stage s ON s.id = l.stage_id
            WHERE l.active = TRUE AND {where_sql}
              AND COALESCE(s.is_won, FALSE) = {won_test}
            ORDER BY l.priority DESC, l.id DESC
            """,
            where_params,
        )
        return [row[0] for row in self.env.cr.fetchall()]

    def _get_company_currency_sale_revenue(self, leads):
        """Return confirmed sales revenue converted to current company currency."""
        company_id = self.env.company
        revenue = 0
        label = "Total Revenue"
        if 'order_ids' in self.env['crm.lead']._fields:
            lead_ids = leads.ids if leads else []
            if lead_ids:
                # One grouped SQL query per (currency, order date) instead
                # of a conversion call per order — the rate is picked at
                # each order's own date exactly like before.
                self.env.cr.execute(
                    """
                    SELECT o.currency_id, DATE(o.date_order),
                           SUM(o.amount_total)
                    FROM sale_order o
                    WHERE o.opportunity_id = ANY(%s) AND o.state = 'sale'
                    GROUP BY 1, 2
                    """,
                    (lead_ids,),
                )
                for currency_id, order_date, amount_sum in \
                        self.env.cr.fetchall():
                    currency = self.env['res.currency'].browse(currency_id)
                    revenue += currency._convert(
                        float(amount_sum),
                        company_id.currency_id,
                        company_id,
                        order_date,
                    )
        else:
            if leads:
                self.env.cr.execute(
                    """
                    SELECT COALESCE(SUM(l.expected_revenue), 0)
                    FROM crm_lead l
                    WHERE l.id = ANY(%s)
                    """,
                    (leads.ids,),
                )
                revenue = float(self.env.cr.fetchone()[0])
            label = "Total Expected Revenue"
        return revenue, label

    def _get_metrics_data(self, domain=None, daterange=None):
        """Calculate key metrics with month-over-month comparison"""
        start_date = next(
            (d[2].split(' ')[0] for d in domain if d[1] == '>='), None)

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

        # Raw SQL: one light query per bucket (won / not-won partition the
        # result set exactly like the old filtered() calls did).
        where_sql, where_params = self._dashboard_where_from_domain(domain)
        access_sql, access_params = self._dashboard_access_conditions()
        bucket_params = access_params + where_params

        current_won_ids = self._dashboard_won_active_ids(
            f"{access_sql} AND {where_sql}", bucket_params, won=True)
        current_active_ids = self._dashboard_won_active_ids(
            f"{access_sql} AND {where_sql}", bucket_params, won=False)
        current_won_leads = self.browse(current_won_ids)
        current_active_leads = self.browse(current_active_ids)
        current_leads_count = len(current_won_ids) + len(current_active_ids)

        prev_won_leads = self.env['crm.lead']
        prev_active_leads = self.env['crm.lead']
        if prev_start_date != datetime.now().date() and prev_end_date != datetime.now().date():
            # Keep the team / salesperson leaves with their OWN operators so
            # multi-select ('in', [...]) filters still apply to the
            # previous-period comparison (the date leaves are dropped here,
            # exactly like the old code did).
            extra_leaves = [
                leaf for leaf in (domain or [])
                if isinstance(leaf, (list, tuple)) and len(leaf) == 3
                and leaf[0] in ('team_id', 'user_id')
            ]
            prev_domain = [
                ('date_closed', '>=', prev_start_date),
                ('date_closed', '<=', prev_end_date),
            ] + extra_leaves
            prev_where_sql, prev_where_params = \
                self._dashboard_where_from_domain(prev_domain)
            prev_params = access_params + prev_where_params

            prev_won_leads = self.browse(self._dashboard_won_active_ids(
                f"{access_sql} AND {prev_where_sql}", prev_params, won=True))
            prev_active_leads = self.browse(self._dashboard_won_active_ids(
                f"{access_sql} AND {prev_where_sql}", prev_params, won=False))

        # Calculate metrics
        current_revenue, label = self._get_company_currency_sale_revenue(
            current_won_leads)
        last_month_revenue, label = self._get_company_currency_sale_revenue(
            prev_won_leads)

        active_leads_count = len(current_active_leads)
        last_month_active_leads = len(prev_active_leads)

        current_conversion_rate = (len(current_won_leads) / current_leads_count
                                   * 100) if current_leads_count else 0
        last_month_conversion_rate = (
                len(prev_won_leads) / len(
            prev_active_leads) * 100) if prev_active_leads else 0

        deals_closed_count = len(current_won_leads)
        last_month_deals_closed = len(prev_won_leads)

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
        domain = list(domain or [])

        # Month windows for the last 6 months (oldest first, like before)
        month_starts = [
            today.replace(day=1) - relativedelta(months=i)
            for i in range(5, -1, -1)
        ]
        first_start = month_starts[0]
        last_end = month_starts[-1] + relativedelta(months=1) - timedelta(
            days=1)

        has_orders = 'order_ids' in self.env['crm.lead']._fields
        revenue_by_month = {}
        leads_counts = {}

        where_sql, where_params = self._dashboard_where_from_domain(domain)
        access_sql, access_params = self._dashboard_access_conditions()

        # Grouping by month must use the same timezone the ORM used (the
        # context tz); dates are stored in UTC.
        tz = self.env.context.get('tz')
        if tz not in pytz.all_timezones_set:
            tz = 'UTC'

        # Leads created per month — one grouped SQL query instead of six
        # searches
        self.env.cr.execute(
            f"""
            SELECT date_trunc('month',
                     l.create_date AT TIME ZONE 'UTC' AT TIME ZONE %s),
                   COUNT(*)
            FROM crm_lead l
            WHERE l.create_date >= %s AND l.create_date <= %s
              AND l.active = TRUE
              AND {access_sql} AND {where_sql}
            GROUP BY 1
            """,
            [tz, first_start, last_end] + access_params + where_params,
        )
        for created_month, count in self.env.cr.fetchall():
            leads_counts[created_month.strftime('%Y-%m')] = count

        # Revenue per month: won leads closed in the window, orders joined
        # and summed in one SQL query (all order states, like before)
        if has_orders:
            self.env.cr.execute(
                f"""
                SELECT date_trunc('month',
                         l.date_closed AT TIME ZONE 'UTC' AT TIME ZONE %s),
                       SUM(o.amount_total)
                FROM crm_lead l
                LEFT JOIN crm_stage s ON s.id = l.stage_id
                JOIN sale_order o ON o.opportunity_id = l.id
                WHERE COALESCE(s.is_won, FALSE) = TRUE
                  AND l.date_closed >= %s AND l.date_closed <= %s
                  AND l.active = TRUE
                  AND {access_sql} AND {where_sql}
                GROUP BY 1
                """,
                [tz, first_start, last_end] + access_params + where_params,
            )
            for closed_month, amount_sum in self.env.cr.fetchall():
                revenue_by_month[closed_month.strftime('%Y-%m')] = \
                    float(amount_sum or 0)

        for month_start in month_starts:
            month_key = month_start.strftime('%Y-%m')
            data.append({
                'month': month_start.strftime('%b'),
                'revenue': revenue_by_month.get(month_key, 0),
                'leads': leads_counts.get(month_key, 0),
            })

        return data

    def _get_pipeline_data(self, domain=None):
        """Get pipeline distribution by stages"""
        stages = self.env['crm.stage'].search([])

        # Raw SQL: total + per-stage counts, two light queries instead of
        # one search per stage (N+1). Record-rule equivalent: multi-company
        # + personal-leads rule (same rows the ORM search returned).
        where_sql, where_params = self._dashboard_where_from_domain(domain)
        access_sql, access_params = self._dashboard_access_conditions()
        sql_params = access_params + where_params

        self.env.cr.execute(
            f"""
            SELECT COUNT(*)
            FROM crm_lead l
            WHERE l.active = TRUE AND {access_sql} AND {where_sql}
            """,
            sql_params,
        )
        total_leads = self.env.cr.fetchone()[0]

        if total_leads == 0:
            return []

        self.env.cr.execute(
            f"""
            SELECT l.stage_id, COUNT(*)
            FROM crm_lead l
            WHERE l.active = TRUE AND {access_sql} AND {where_sql}
            GROUP BY l.stage_id
            """,
            sql_params,
        )
        counts_by_stage = {
            stage_id: count for stage_id, count in self.env.cr.fetchall()
        }

        pipeline_data = []
        colors = ['#4C5814', '#7E8C2F', '#A9B85A', '#D3C91F',
                  '#48521B', '#8B9A3E', '#BCC680', '#DDE3C0']

        for i, stage in enumerate(stages):
            leads_in_stage = counts_by_stage.get(stage.id, 0)
            percentage = round((leads_in_stage / total_leads) * 100, 1)

            if percentage > 0:  # Only include stages with leads
                pipeline_data.append({
                    'stage': stage.name,
                    'value': percentage,
                    'count': leads_in_stage,
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
        # Raw SQL: visible lead ids (record-rule equivalent) + one joined
        # query for the activities instead of ORM field prefetching.
        where_sql, where_params = self._dashboard_where_from_domain(domain)
        access_sql, access_params = self._dashboard_access_conditions()

        self.env.cr.execute(
            f"SELECT l.id FROM crm_lead l WHERE l.active = TRUE "
            f"AND {access_sql} AND {where_sql}",
            access_params + where_params,
        )
        lead_ids = [row[0] for row in self.env.cr.fetchall()]

        self.env.cr.execute(
            """
            SELECT t.name->>%s, t.name->>'en_US', a.date_deadline, p.name
            FROM mail_activity a
            LEFT JOIN mail_activity_type t ON t.id = a.activity_type_id
            JOIN res_users u ON u.id = a.user_id
            LEFT JOIN res_partner p ON p.id = u.partner_id
            WHERE a.res_model = 'crm.lead'
              AND a.res_id = ANY(%s)
              AND a.date_deadline >= %s
              AND a.date_deadline <= %s
            ORDER BY a.date_deadline ASC, a.id ASC
            """,
            (
                self.env.lang or 'en_US',
                lead_ids,
                start_date,
                end_date,
            ),
        )
        for type_name, type_name_en, deadline, user_name in \
                self.env.cr.fetchall():
            activity_data.append({
                'name': (type_name or type_name_en) or False,
                'date_deadline': str(deadline),
                'user_name': user_name or False,
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

        # Strip the logged-in-user restriction: every salesperson must be
        # counted against their OWN deals. Keeping the caller's user_id leaf
        # here would AND "user_id = performer" with "user_id = current user",
        # so only the logged-in user could ever show up.
        date_domain = [
            leaf for leaf in (domain or [])
            if isinstance(leaf, (list, tuple)) and len(leaf) == 3
            and leaf[0] in ('date_closed', 'team_id', 'create_date')
        ]
        # One raw SQL grouped query: per-salesperson deal count + expected
        # revenue sum, instead of one search per salesperson (N+1).
        # sudo()-equivalent: the old code searched with sudo() so the
        # plain salesman's record rules don't hide other users' leads.
        # (The "won" condition is applied directly in the SQL below, so it
        # must not be part of the domain passed to the WHERE builder.)
        won_where_sql, won_where_params = self._dashboard_where_from_domain(
            [
                ('date_closed', '>=', start_date),
                ('date_closed', '<=', end_date),
            ] + date_domain)
        self.env.cr.execute(
            f"""
            SELECT l.user_id, COUNT(*), COALESCE(SUM(l.expected_revenue), 0)
            FROM crm_lead l
            LEFT JOIN crm_stage s ON s.id = l.stage_id
            WHERE COALESCE(s.is_won, FALSE) = TRUE
              AND l.active = TRUE AND {won_where_sql}
            GROUP BY l.user_id
            """,
            won_where_params,
        )
        # Consume the result immediately — any ORM access below (image
        # prefetch…) runs its own queries on the same cursor and would
        # overwrite this result set.
        won_rows = self.env.cr.fetchall()

        allowed_ids = set(salespeople.ids)
        sudo_users = salespeople.sudo()
        avatars = {user.id: bool(user.image_128) for user in sudo_users}

        performers = []
        for user_id, deals_count, total_amount in won_rows:
            # Only sales people with deals (empty groups / non-salesman
            # owners are skipped, same as the old per-user loop)
            if not user_id or user_id not in allowed_ids:
                continue
            user = sudo_users.browse(user_id) if user_id in avatars \
                else None

            performers.append({
                'name': user.name,
                'deals': deals_count,
                'amount': float(total_amount),
                # Use the /web/image controller instead of inline base64 —
                # image_128 already returns base64 text, and serving via the
                # controller avoids encoding/oversize payload issues.
                'user_id': user_id,
                'avatar': avatars.get(user_id, False),
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

        # One query for all related activities instead of one per lead
        self.env['mail.activity'].search([
            ('res_model', '=', 'crm.lead'),
            ('res_id', 'in', lead_ids),
        ]).write({'is_dismissed_notification': True})

        return True

    @api.model
    def mark_as_read(self, lead_ids):
        """Mark lead notifications as read"""
        leads = self.browse(lead_ids).sudo()
        leads.write({'is_marked_as_read': True})

        # One query for all related activities instead of one per lead
        activities = self.env['mail.activity'].search([
            ('res_model', '=', 'crm.lead'),
            ('res_id', 'in', lead_ids),
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
            ], order='create_date desc')
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
            ], order='date_deadline desc')

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

            # Single SQL query for the average instead of reading every
            # matching lead
            self.env.cr.execute(
                """
                SELECT COALESCE(SUM(l.expected_revenue), 0), COUNT(*)
                FROM crm_lead l
                WHERE l.active = TRUE AND l.expected_revenue > 0
                """,
            )
            revenue_sum, lead_count = self.env.cr.fetchone()
            if lead_count:
                avg_val = float(revenue_sum) / lead_count
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

            # Final sorting & limiting (frontend shows all with scroll)
            return sorted(notifications, key=lambda x: x['create_date'],
                          reverse=True)[:50]


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
