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
from odoo import fields, models, tools


class SubscriptionReport(models.Model):
    """Model for the subscription report"""
    _name = 'subscription.report'
    _description = 'Subscription Report'
    _auto = False

    partner_id = fields.Many2one('res.partner', string='Customer')
    state_subscription = fields.Selection(
        selection=[('quotation', 'Quotation'), ('active', 'Active'),
                   ('renew', 'Renew'), ('churned', 'Churned'),
                   ('trial', 'On Trial')],
        string='Subscription State')
    time_based_price_id = fields.Many2one('time.based.price', string='Recurrence')
    state = fields.Selection(
        selection=[('draft', 'Draft'), ('sale', 'Sale'), ('posted', 'Posted'), ('requested', 'Requested')], string='Status')
    company_id = fields.Many2one('res.company', string='Company')
    recurring_revenue = fields.Float(string='Monthly Recurring Revenue')
    weekly_price_sum = fields.Float(string='Weekly Revenue')
    monthly_price_sum = fields.Float(string='Monthly Revenue')
    yearly_price_sum = fields.Float(string='Yearly Revenue')
    arr = fields.Float(string='ARR', help='Annual Recurring Revenue')
    nrr = fields.Float(string='NRR')
    mrr_change = fields.Float(string='MRR Change')
    arr_change = fields.Float(string='ARR Change')
    subscription_count = fields.Integer(string='Subscription Count')
    active_subscription_count = fields.Integer(string='Active')
    trial_subscription_count = fields.Integer(string='Trial')
    churned_subscription_count = fields.Integer(string='Churned')
    renewal_count = fields.Integer(string='Renewals', help="Subscriptions in Renew state")
    number_of_product_sold = fields.Integer(string='Products Sold')
    start_date = fields.Datetime(string='Start Date')
    next_invoice_date = fields.Datetime(string='Next Invoice Date')
    end_date = fields.Datetime(string='End Date')
    trial_end_date = fields.Datetime(string='Trial End Date')
    product_name = fields.Char(string='Product')
    plan_name = fields.Char(string='Plan')
    recurrence_name = fields.Char(string='Recurrence Type')
    id = fields.Integer()

    def init(self):
        """Function fetch data to show on the report"""
        tools.drop_view_if_exists(self._cr, 'subscription_report')
        self._cr.execute("""
            CREATE OR REPLACE VIEW subscription_report AS (
                SELECT 
                    so.id AS id,
                    so.partner_id AS partner_id,
                    so.company_id AS company_id,
                    so.state_subscription AS state_subscription,
                    so.state AS state,
                    so.time_based_price_id AS time_based_price_id,
                    so.create_date AS start_date,
                    so.renewal_date AS next_invoice_date,
                    so.end_date AS end_date,
                    so.trial_end AS trial_end_date,
                    pt.name AS product_name,
                    sot.name AS plan_name,
                    tbp.name AS recurrence_name,

                    -- Metrics
                    1 AS subscription_count,
                    sol.total_price AS recurring_revenue,
                    1 AS number_of_product_sold,

                    -- Boolean based counts
                    CASE WHEN so.state_subscription = 'active' THEN 1 ELSE 0 END AS active_subscription_count,
                    CASE WHEN so.state_subscription = 'trial' THEN 1 ELSE 0 END AS trial_subscription_count,
                    CASE WHEN so.state_subscription = 'churned' THEN 1 ELSE 0 END AS churned_subscription_count,
                    CASE WHEN so.state_subscription = 'renew' THEN 1 ELSE 0 END AS renewal_count,

                    -- Revenue Breakdown
                    CASE WHEN tbp.subscription_unit = 'weeks' THEN sol.total_price ELSE 0 END AS weekly_price_sum,
                    CASE WHEN tbp.subscription_unit = 'months' THEN sol.total_price ELSE 0 END AS monthly_price_sum,
                    CASE WHEN tbp.subscription_unit = 'years' THEN sol.total_price ELSE 0 END AS yearly_price_sum,

                    -- ARR Calculation
                    CASE 
                        WHEN tbp.subscription_unit = 'months' THEN sol.total_price * 12
                        WHEN tbp.subscription_unit = 'weeks' THEN sol.total_price * 52
                        WHEN tbp.subscription_unit = 'years' THEN sol.total_price
                        ELSE sol.total_price * 12
                    END AS arr,

                    0.0 AS nrr,
                    0.0 AS mrr_change,
                    0.0 AS arr_change

                FROM subscription_order so
                LEFT JOIN subscription_order_line sol ON so.id = sol.subscription_order_id
                LEFT JOIN time_based_price tbp ON so.time_based_price_id = tbp.id
                LEFT JOIN product_product pp ON sol.product_id = pp.id
                LEFT JOIN product_template pt ON pp.product_tmpl_id = pt.id
                LEFT JOIN sale_order_template sot ON so.sale_order_template_id = sot.id
            )
        """)