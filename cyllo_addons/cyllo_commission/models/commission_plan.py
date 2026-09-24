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
from calendar import monthrange
from datetime import date

from dateutil.relativedelta import relativedelta
from odoo import Command, api, fields, models
from odoo.exceptions import UserError, ValidationError


class CommissionPlan(models.Model):
    """Commission plan for Sales """
    _name = 'commission.plan'
    _description = 'Commission plan'
    _inherit = ['mail.thread']

    name = fields.Char(string='Name', required=True, copy=False)
    active = fields.Boolean(string='Active', default=True)
    date_from = fields.Date(string='From', required=True,
                            default=lambda self: date.today().replace(month=1,
                                                                      day=1))
    date_to = fields.Date(string='To', required=True,
                          default=lambda self: date.today().replace(month=12,
                                                                    day=31))
    type = fields.Selection(
        selection=[
            ('target', 'Targets'),
            ('contribution', 'Contributions'),
        ],
        string='Type',
        default='target',
        required=True,
        readonly=True,
    )
    user_type = fields.Selection(
        selection=[
            ('team', 'Sales Team'),
            ('person', 'Salesperson')
        ],
        default='team',
        required=True,
        copy=False
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('approved', 'Approved'),
            ('done', 'Done'),
            ('rejected', 'Rejected'),
        ],
        default='draft',
        required=True,
        copy=False
    )
    company_id = fields.Many2one('res.company', store=True, copy=False,
                                 string="Company",
                                 default=lambda
                                     self: self.env.user.company_id.id)
    currency_id = fields.Many2one('res.currency', string="Currency",
                                  related='company_id.currency_id',
                                  default=lambda
                                      self: self.env.user.company_id.currency_id.id)
    team_id = fields.Many2one('crm.team', string="Sales Team")
    user_ids = fields.One2many('commission.plan.user',
                               'plan_id', string='Sales people',
                               required=True)
    commission_amount = fields.Monetary(string='On Target Commission',
                                        default=1000)
    frequency = fields.Selection(
        selection=[
            ('monthly', 'Monthly'),
            ('quarterly', 'Quarterly'),
            ('yearly', 'Yearly')
        ],
        default='monthly',
        required=True,
    )
    target_commission_ids = fields.One2many(
        'commission.plan.target.commission', 'plan_id')
    contribution_ids = fields.One2many('commission.contribution',
                                       'plan_id')
    commission_frequency_ids = fields.One2many(
        'commission.plan.frequency', 'plan_id')
    commission_report_ids = fields.One2many('commission.report',
                                            'plan_id',
                                            compute='_compute_commission_report_ids',
                                            store=True)
    type_id = fields.Many2one('commission.type',
                              string='Type',
                              copy=False, )
    sales_people_user_ids = fields.Many2many('res.users',
                                             relation='crm_commission_plan_sales_people_user_rel',
                                             column1='plan_id',
                                             column2='user_id',
                                             compute='_compute_sales_people_user_ids',
                                             store=True
                                             )
    duplicate_user_ids = fields.Many2many('res.users',
                                          relation='crm_commission_plan_duplicate_users_rel',
                                          column1='plan_id',
                                          column2='user_id',
                                          compute='_compute_duplicate_user_ids',
                                          store=True
                                          )
    user_id = fields.Many2one('res.users', string='User',
                              default=lambda self: self.env.user,
                              )
    is_bonus_commission = fields.Boolean(string="Bonus Commission",
                                         compute='_compute_is_bonus_commission',
                                         store=True)
    mail_sent_user_ids = fields.Many2many('res.users',
                                          string='Users Already Notified',
                                          relation='crm_commission_plan_mail_sent_users_rel',
                                          column1='plan_id',
                                          column2='user_id',
                                          readonly=True)
    welcome_mail_sent_user_ids = fields.Many2many('res.users',
                                                  string='Users Already Welcomed',
                                                  relation='crm_commission_plan_welcome_mail_sent_users_rel',
                                                  column1='plan_id',
                                                  column2='user_id',
                                                  readonly=True)
    type_ids = fields.Many2many('commission.type',
                                relation='commission_plan_type_rel',
                                column1='plan_id',
                                column2='type_id',
                                compute='_compute_type_ids',
                                store=True
                                )
    total_commission = fields.Float(string='Total Commission',
                                    compute='_compute_total_commission',
                                    store=True)

    _sql_constraints = [
        ('commission_name', 'unique (name)',
         "The Commission plan name Already exist.")
    ]

    @api.depends(
        'state',
        'team_id.order_ids.opportunity_id.stage_id',
        'team_id.order_ids.state',
        'team_id.order_ids.payment_state',
        'team_id.order_ids.order_line.price_subtotal_latest',
        'user_ids.user_id.order_ids.opportunity_id.stage_id',
        'user_ids.user_id.order_ids.state',
        'user_ids.user_id.order_ids.payment_state',
        'user_ids.user_id.order_ids.order_line.price_subtotal_latest',
    )
    def _compute_commission_report_ids(self):
        """Compute commission reports once state is approved and
        required dependencies change."""
        for record in self:
            record.commission_report_ids = []  # Default empty
            if record.state != 'approved':
                continue

            today = date.today()
            plan = record
            period_type = record.frequency
            target_commissions = record.target_commission_ids
            sale_orders = record._get_related_order_lines_and_orders()
            all_orders = sale_orders['orders']
            all_order_lines = sale_orders['order_lines']
            commission_reports = []
            if record.user_type == 'team':
                members = self.env['crm.team.member'].search([
                    ('crm_team_id', '=', record.team_id.id)
                ]).mapped('user_id')
                salespeople = self.env['commission.plan.user']
            else:
                salespeople = record.user_ids
                members = salespeople.mapped('user_id')
            for user in members:
                if user in record.duplicate_user_ids:
                    continue
                user_salesperson = salespeople.filtered(
                    lambda p: p.user_id == user) if salespeople else []
                user_date_from = user_salesperson.date_from if user_salesperson else None
                user_date_to = user_salesperson.date_to if user_salesperson else None
                for period in record.commission_frequency_ids:
                    source_orders = []
                    from_date = max(period.date_from,
                                    user_date_from) if user_date_from else period.date_from
                    to_date = min(period.date_to,
                                  user_date_to) if user_date_to else period.date_to
                    valid_period = self._is_valid_commission_period(period_type,
                                                                    to_date,
                                                                    today)
                    if record.type == 'target':
                        source_orderlines = []
                        user_orders = all_orders.filtered(lambda
                                                              o: from_date <= o.order_date <= to_date and o.user_id == user)
                        periodic_order_lines = all_order_lines.search(
                            [('order_id', 'in',
                              user_orders.ids)]) if all_order_lines else \
                            self.env['sale.order.line']
                        order_ids = user_orders.mapped('id')
                        periodic_order_lines_ids = periodic_order_lines.mapped(
                            'id')
                        for id in order_ids:
                            source_orders.append(id)
                        for id in periodic_order_lines_ids:
                            source_orderlines.append(id)
                        total_amount = sum(
                            periodic_order_lines.mapped(
                                'price_subtotal_latest')) if periodic_order_lines else sum(
                            user_orders.mapped('amount_untaxed_latest'))
                        if period.amount:
                            achieved_pct = (total_amount / period.amount)
                            matched_rates = target_commissions.filtered(
                                lambda p: achieved_pct >= p.target_rate
                            )
                            if matched_rates:
                                commission_target_rate = max(
                                    matched_rates.mapped('target_rate'))
                                commission_target = target_commissions.filtered(
                                    lambda
                                        c: c.target_rate == commission_target_rate
                                )
                                if commission_target and commission_target.amount > 0 and valid_period:
                                    target_rate = commission_target.target_rate
                                    commission_amount = commission_target.amount
                                    order = self.env['sale.order']
                                    self.prepare_commission_reports(plan, user,
                                                                    period,
                                                                    total_amount,
                                                                    target_rate,
                                                                    commission_amount,
                                                                    order,
                                                                    commission_reports,
                                                                    source_orders,
                                                                    source_orderlines)
                    elif record.type == 'contribution':
                        for contribution in record.contribution_ids:
                            target_rate = 0.0
                            self._process_contribution_commissions(
                                contribution.type_id.type,
                                contribution.rate,
                                contribution.order_ids,
                                contribution.order_line_ids,
                                user,
                                from_date, to_date,
                                valid_period, period_type, today,
                                plan, period, target_rate,
                                commission_reports, source_orders)
            record.commission_report_ids = commission_reports

    @api.depends('user_type', 'team_id', 'team_id.crm_team_member_ids',
                 'user_ids.user_id', 'user_ids.user_id.team_id')
    def _compute_sales_people_user_ids(self):
        """Compute and store the salespeople assigned for the commission plan"""
        for record in self:
            users = self.env['res.users']  # start with empty recordset
            if record.user_type == 'team' and record.team_id:
                users = self.env['crm.team.member'].search([
                    ('crm_team_id', '=', record.team_id.id)
                ]).mapped('user_id')
            elif record.user_type == 'person' and record.user_ids:
                users = record.user_ids.mapped('user_id')
            record.sales_people_user_ids = users

    @api.depends('state', 'sales_people_user_ids', 'type_ids', )
    def _compute_duplicate_user_ids(self):
        for record in self:
            record.duplicate_user_ids = []
            if record.state == 'approved':
                types = record.type_ids
                same_plan_type_commissions = self.env['commission.plan'].search(
                    [
                        ('id', '!=', record.id),
                        ('type_ids', 'in', types.ids),
                        ('state', '=', 'approved')
                    ])
                existing_users = same_plan_type_commissions.mapped(
                    'sales_people_user_ids')
                record.duplicate_user_ids = existing_users & record.sales_people_user_ids

    @api.depends('target_commission_ids')
    def _compute_is_bonus_commission(self):
        """Store that this commission plan have Bonus for over achievement"""
        for record in self:
            bonus_commissions = record.target_commission_ids.filtered(
                lambda b: b.amount_rate > 1)
            if bonus_commissions:
                record.is_bonus_commission = True
            else:
                record.is_bonus_commission = False

    @api.depends('type', 'type_id', 'contribution_ids.type_id')
    def _compute_type_ids(self):
        """Store plan type ids of the plan"""
        for record in self:
            if record.type == 'target' and record.type_id:
                record.type_ids = record.type_id
            elif record.type == 'contribution' and record.contribution_ids:
                record.type_ids = record.contribution_ids.mapped('type_id')
            else:
                record.type_ids = []

    @api.depends('commission_report_ids',
                 'commission_report_ids.commission_amount')
    def _compute_total_commission(self):
        for record in self:
            record.total_commission = 0.0
            if record.commission_report_ids:
                record.total_commission = sum(
                    record.commission_report_ids.mapped('commission_amount'))

    @api.constrains('user_type')
    def _check_user_type(self):
        """Ensure team is selected for sale-team commission plan"""
        for record in self:
            if record.user_type == 'team':
                record.user_ids = False
                if record.user_type == 'team' and not record.team_id:
                    raise UserError(
                        "Please add a Sales Team to the commission plan.")
            else:
                record.team_id = False
                if not record.user_ids:
                    raise UserError(
                        "Please add a user to the commission plan.")

    @api.constrains('type')
    def _check_type_id(self):
        """Ensure type_id is selected for type target"""
        for record in self:
            if record.type == 'target' and not record.type_id:
                raise UserError(
                    "Please add Type to the commission plan.")
            elif record.type == 'contribution':
                record.type_id = False
                if not record.contribution_ids:
                    raise UserError(
                        "Please add contribution type to the commission plan.")

    @api.constrains('type_ids', 'user_ids', 'team_id')
    def _check_similar_commission(self):
        """This constraint ensures that a commission plan does not have duplicate assignments of users or teams under the same plan type.
            It first gathers all other commission plans with the same plan type and checks if any users are already assigned to them.
            If the user type is 'team', it ensures that no other plan exists with the same team and plan type, and that no user from the team
            is already assigned to another plan of the same type. If the user type is 'person', it checks whether any selected users
            are already linked to other commission plans with the same plan type either through direct assignment or via other users in the plan.
            If any duplicates are found in either case, a ValidationError is raised to prevent overlapping commission assignments."""
        for record in self:
            if not record.type_ids:
                continue
            domain = [
                ('id', '!=', record.id),
                ('type_ids', 'in', record.type_ids.ids),
                ('state', 'not in', ['done', 'rejected']),
                ('date_from', '<=', record.date_to),
                ('date_to', '>=', record.date_from),
            ]
            if record.user_type == 'team' and record.team_id:
                similar_team_plans = self.env['commission.plan'].search(
                    domain).filtered(lambda t: t.team_id == record.team_id)
                same_plan_types = similar_team_plans.mapped('type_ids')
                plan_name = same_plan_types.mapped('name')
                if similar_team_plans:
                    raise ValidationError(
                        f"Sales Team with  plan types {', '.join(plan_name)} already exists.")
            if record.user_type == 'person' and record.user_ids:
                sales_people = record.user_ids.mapped('user_id')
                domain.append(('sales_people_user_ids', 'in', sales_people.ids))
                similar_plans = self.env['commission.plan'].search(domain)
                existing_users = similar_plans.mapped('sales_people_user_ids')
                if existing_users & sales_people:
                    common_users = existing_users & sales_people
                    names = common_users.mapped('name')
                    same_plan_types = similar_plans.mapped('type_ids')
                    plan_name = same_plan_types.mapped('name')
                    raise ValidationError(
                        f"Sales people: {', '.join(names)} already exists in the Plan Type: {', '.join(plan_name)}.")

    @api.onchange('type')
    def _onchange_fill_default_commissions(self):
        """Call function to create default commission target% and OTC%"""
        if self.type == 'target':
            amount = self.commission_amount
            self.target_commission_ids = self.prepare_default_commission_lines(
                amount)
            self.type_ids = []
            self.contribution_ids = [Command.clear()]
        else:
            self.target_commission_ids = [Command.clear()]
            self.type_ids = []

    @api.onchange('commission_amount')
    def _onchange_commission_amount(self):
        """Change the OTC amounts accordingly when we change the commission amount"""
        for line in self.target_commission_ids:
            if line.amount_rate == 1.0:
                line.amount = self.commission_amount
            line._compute_amount()

    @api.onchange('frequency', 'date_from', 'date_to')
    def _onchange_commission_frequency(self):
        """Function will call the functions create frequencies respectively"""
        for record in self:
            record.commission_frequency_ids = [Command.clear()]
            if not record.date_from or not record.date_to:
                continue
            if record.frequency == 'monthly':
                record.commission_frequency_ids = record.prepare_monthly_frequencies()
            elif record.frequency == 'quarterly':
                record.commission_frequency_ids = record.prepare_quarterly_frequencies()
            elif record.frequency == 'yearly':
                record.commission_frequency_ids = record.prepare_yearly_frequencies()

    def write(self, vals):
        """Custom write to handle commission report deletion and salesperson sync"""
        fields_triggering_report_unlink = {
            'commission_frequency_ids', 'type_id', 'contribution_ids',
            'target_commission_ids', 'commission_amount', 'team_id',
            'user_ids', 'user_type', 'date_from', 'date_to'
        }
        if fields_triggering_report_unlink.intersection(vals):
            self.mapped('commission_report_ids').unlink()
        return super().write(vals)

    def action_approve(self):
        """Approve Button action"""
        for record in self:
            record.state = 'approved'
            new_users = record.duplicate_user_ids - record.mail_sent_user_ids
            welcome_users = (
                                    record.sales_people_user_ids - record.duplicate_user_ids) - record.welcome_mail_sent_user_ids
            for user in new_users:
                if record.type == 'target':
                    template = record.env.ref(
                        'cyllo_commission.email_template_duplicate_commission_plan')
                    template.with_context({
                        'user': user.id,
                        'name': user.name,
                        'email_to': user.email,
                        'types': [],
                    }).send_mail(record.id, force_send=False)
                else:
                    plans = self.env['commission.plan'].search([
                        ('sales_people_user_ids', 'in', user.id),
                        ('id', '!=', record.id)
                    ])
                    current_types = record.type_ids.ids
                    types = []
                    for plan in plans:
                        types.extend(plan.type_ids.ids)
                    duplicate_types = list(set(types) & set(current_types))
                    template = record.env.ref(
                        'cyllo_commission.email_template_duplicate_commission_plan')
                    template.with_context({
                        'user': user.id,
                        'name': user.name,
                        'email_to': user.email,
                        'types': duplicate_types,
                    }).send_mail(record.id, force_send=False)
            for user in welcome_users:
                template = record.env.ref(
                    'cyllo_commission.email_template_notify_user')
                template.with_context({
                    'user': user.id,
                    'name': user.name,
                    'email_to': user.email,
                }).send_mail(record.id, force_send=False)
            record.mail_sent_user_ids = record.mail_sent_user_ids | new_users
            record.welcome_mail_sent_user_ids = record.welcome_mail_sent_user_ids | welcome_users

    def action_reject(self):
        """Cancel Button action"""
        self.state = 'rejected'

    def action_done(self):
        """Done Button action"""
        self.state = 'done'

    def action_draft(self):
        """Reset to draft Button action"""
        self.state = 'draft'

    def action_open_commission(self):
        """Action for show commission report of the Commission plan"""
        self.ensure_one()
        if self.type == 'target':
            tree_view = self.env.ref(
                'cyllo_commission.view_target_commission_report_plan_tree')
            form_view = self.env.ref(
                'cyllo_commission.view_target_commission_report_form')
        else:
            tree_view = self.env.ref(
                'cyllo_commission.view_contribution_commission_report_plan_tree')
            form_view = self.env.ref(
                'cyllo_commission.view_contribution_commission_report_form')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Commissions',
            'view_mode': 'tree,form',
            'res_model': 'commission.report',
            'views': [
                (tree_view.id, 'tree'),
                (form_view.id, 'form'),
            ],
            'domain': [('plan_id', '=', self.id)],
            'context': {'default_plan_id': self.id},
        }

    def _send_reminder_action(self):
        today = date.today()
        plans = self.search([('date_to', '<', today), ('state', '!=', 'done')])
        for plan in plans:
           plan.state = 'done'

    def prepare_default_commission_lines(self, amount):
        """Create the default commission lines"""
        return [
            Command.create({
                'target_rate': 0.0,
                'amount': 0.0,
                'amount_rate': 0.0,
                'currency_id': self.env.company.currency_id.id,
            }),
            Command.create({
                'target_rate': 0.5,
                'amount': 0.0,
                'amount_rate': 0.5,
                'currency_id': self.env.company.currency_id.id,
            }),
            Command.create({
                'target_rate': 1.0,
                'amount': amount,
                'amount_rate': 1.0,
                'currency_id': self.env.company.currency_id.id,
            }),
        ]

    def prepare_monthly_frequencies(self):
        """Create monthly periods according to the start date & end date of commission plan"""
        self.ensure_one()
        frequency_vals = []
        current_date = self.date_from.replace(day=1)
        while current_date <= self.date_to:
            last_day = monthrange(current_date.year, current_date.month)[1]
            date_to = current_date.replace(day=last_day)
            frequency_vals.append(Command.create({
                'name': current_date.strftime('%b %Y'),
                'date_from': current_date,
                'date_to': date_to,
            }))
            current_date += relativedelta(months=1)
        return frequency_vals

    def prepare_quarterly_frequencies(self):
        """Create quarterly periods according to the start date & end date of commission plan"""
        self.ensure_one()
        frequency_vals = []
        current_date = self.date_from.replace(day=1)
        while current_date <= self.date_to:
            year = current_date.year
            month = current_date.month
            quarter = ((month - 1) // 3) + 1
            quarter_start = current_date.replace(month=(3 * (quarter - 1) + 1),
                                                 day=1)
            quarter_end_month = 3 * quarter
            days_in_end_month = monthrange(year, quarter_end_month)[1]
            quarter_end = current_date.replace(month=quarter_end_month,
                                               day=days_in_end_month)
            if quarter_end > self.date_to:
                quarter_end = self.date_to
            frequency_vals.append(Command.create({
                'name': f"{year} Q{quarter}",
                'date_from': quarter_start,
                'date_to': quarter_end,
            }))
            current_date = quarter_start + relativedelta(months=3)
        return frequency_vals

    def prepare_yearly_frequencies(self):
        """Create Yearly periods according to the start date & end date of commission plan"""
        self.ensure_one()
        frequency_vals = []
        current_year = self.date_from.year
        while current_year <= self.date_to.year:
            year_start = date(current_year, 1, 1)
            year_end = date(current_year, 12, 31)
            if year_start < self.date_from:
                year_start = self.date_from
            if year_end > self.date_to:
                year_end = self.date_to
            frequency_vals.append(Command.create({
                'name': str(current_year),
                'date_from': year_start,
                'date_to': year_end,
            }))
            current_year += 1
        return frequency_vals

    def prepare_commission_reports(self, plan, user, period, total_amount,
                                   target_rate, commission_amount, order,
                                   commission_reports, source_orders,
                                   source_orderlines):
        report_vals = {
            'plan_id': plan.id,
            'user_id': user.id,
            'period_id': period.id,
            'achieve_amount': total_amount,
            'commission_amount': commission_amount,
            'achieve_rate': target_rate,
            'order_id': order.id,
            'order_ids': source_orders,
            'orderline_ids': source_orderlines,
            'date': order.order_date,
            'target_amount': period.amount if plan.type == 'target' else 0.0,
        }
        domain = [('plan_id', '=', plan.id), ('user_id', '=', user.id),
                  ('period_name', '=', period.name), ]
        if plan.type == 'contribution':
            domain.append(('order_id', '=', order.id))

        report_model = self.env['commission.report']
        existing_report = report_model.search(domain, limit=1)

        if existing_report:
            existing_report.write(report_vals)
        else:
            commission_reports.append(Command.create(report_vals))

    def _is_valid_commission_period(self, period_type, to_date, today):
        """Return True if the given to_date is in current or past period, based on period_type."""
        if period_type == 'monthly':
            return to_date.month <= today.month and to_date.year <= today.year
        elif period_type == 'quarterly':
            def get_quarter(date):
                return (date.month - 1) // 3 + 1

            current_quarter = get_quarter(today)
            to_quarter = get_quarter(to_date)
            return to_date.year < today.year or (
                    to_date.year == today.year and to_quarter <= current_quarter)
        elif period_type == 'yearly':
            return to_date.year <= today.year
        return False

    def _get_related_order_lines_and_orders(self):
        """Return order lines and corresponding orders based on the plan type and rules."""
        self.ensure_one()
        order_lines = self.env['sale.order.line']
        orders = self.env['sale.order']
        if self.type_id.type == 'sale':
            domain = []
            if self.type_id.sales_rule_to_apply:
                domain = eval(self.type_id.sales_rule_to_apply)
            domain.append(('order_id.is_paid', '=', True))
            order_lines = self.env['sale.order.line'].search(domain)
            orders = order_lines.mapped('order_id')
        elif self.type_id.type == 'crm':
            domain = []
            if self.type_id.crm_rule_to_apply:
                domain = eval(self.type_id.crm_rule_to_apply)
            leads = self.env['crm.lead'].search(domain)
            orders = self.env['sale.order'].search([
                ('opportunity_id', 'in', leads.ids),
                ('is_paid', '=', True)
            ])
            order_lines = orders.mapped('order_line')
        return {
            'order_lines': order_lines,
            'orders': orders}

    def _process_contribution_commissions(self, contribution_type, rate,
                                          orders, order_lines, user,
                                          from_date, to_date, valid_period,
                                          period_type, today, plan, period,
                                          target_rate,
                                          commission_reports, source_orders):
        """Function which filter and pass data to create contribution commission reports"""

        if contribution_type == 'sale':
            user_order_lines = order_lines.filtered(
                lambda
                    o: from_date <= o.order_id.order_date <= to_date and o.order_id.user_id == user
            )
            user_orders = user_order_lines.mapped('order_id')
            for order in user_orders:
                source_orderlines = []
                lines = user_order_lines.filtered(lambda l: l.order_id == order)
                for line in lines:
                    source_orderlines.append(line.id)
                total_amount = sum(lines.mapped('price_subtotal_latest'))
                commission_amount = total_amount * rate
                valid_period = self._is_valid_commission_period(
                    period_type, to_date, today)
                if commission_amount >= 0 and valid_period:
                    self.prepare_commission_reports(plan, user, period,
                                                    total_amount,
                                                    target_rate,
                                                    commission_amount,
                                                    order,
                                                    commission_reports,
                                                    source_orders,
                                                    source_orderlines)
        else:
            user_orders = orders.filtered(
                lambda
                    o: from_date <= o.order_date <= to_date and o.user_id == user)
            for order in user_orders:
                total_amount = order.amount_untaxed_latest
                commission_amount = total_amount * rate
                if commission_amount >= 0 and valid_period:
                    self.prepare_commission_reports(plan, user, period,
                                                    total_amount,
                                                    target_rate,
                                                    commission_amount,
                                                    order,
                                                    commission_reports)
