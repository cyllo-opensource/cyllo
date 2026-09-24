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
from dateutil.relativedelta import relativedelta
from itertools import groupby
from operator import itemgetter
import logging

from odoo import _, api, fields, models
from odoo.tools import format_date
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class SubscriptionOrder(models.Model):
    """Model Subscription order"""
    _name = "subscription.order"
    _description = 'Subscription Order'
    _inherit = ['mail.thread', 'portal.mixin', 'mail.activity.mixin']

    name = fields.Char(string='Reference Number', copy=False, readonly=True,
                       help='Reference number to identify the order')
    partner_id = fields.Many2one('res.partner', string='Customer',
                                 help='Name of the customer', readonly=True)
    subscription_order_line_ids = fields.One2many('subscription.order.line',
                                                  'subscription_order_id',
                                                  string='Order Line',
                                                  help='Subscription order line')
    sale_order_id = fields.Many2one('sale.order',
                                    help='Corresponding sale order id is saved in the field')
    sale_order_line_id = fields.Many2one('sale.order.line', string="Sales Order Line", ondelete='cascade')
    state_subscription = fields.Selection(
        selection=[('quotation', 'Quotation'), ('active', 'Active'),
                   ('renew', 'Renew'), ('churned', 'Churned'),
                   ('trial', 'On Trial')], default='active',
        string='Subscription State',
        help='State of the subscription order shows here')
    renewal_date = fields.Datetime(string='Next Invoice Date',
                                   help='Date to renew the subscription')
    sale_order_template_id = fields.Many2one('sale.order.template',
                                             string='Subscription Plan',
                                             help='Plan chosen in order shows here')
    time_based_price_id = fields.Many2one('time.based.price',
                                          string='Recurrence', required=True)
    invoice_count = fields.Integer(compute='_compute_invoice_count',
                                   help='Count of the invoice')
    state = fields.Selection(
        selection=[('draft', 'Draft'), ('sale', 'Sale'), ('posted', 'Posted'),('requested', 'Requested'),],
        default='draft',
        help='State of the order')
    recurring_revenue = fields.Float(string='MRR',
                                     help='Monthly recurring revenue',
                                     compute='_compute_recurring_revenue',
                                     store=True)
    company_id = fields.Many2one('res.company',
                                 default=lambda self: self.env.company,
                                 help='Current logged in company shows here')
    trial_end = fields.Datetime(string='Trial End Date', related="sale_order_line_id.trial_end", readonly=False,
                                help='Trial period ending date',store=True, copy=False)
    partner_street = fields.Char(compute='_compute_partner_street', store=True,
                                 help='Main street of partner shows here')
    partner_city = fields.Char(related='partner_id.city', string='City')
    partner_state = fields.Char(related='partner_id.state_id.name')
    check_upsell_renewal = fields.Boolean(string='Check Upsell/Renewal',
                                          help='Check if the button clicked is renewal or upsell')
    account_move_ids = fields.Many2many('account.move', string='Invoices',
                                        help='Invoice records store here')
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  help='Currency of the order',
                                  default=lambda self: self.env.company.currency_id)
    amount_untaxed = fields.Monetary(string='Untaxed Amount',
                                     compute='_compute_amounts')
    amount_tax = fields.Monetary(string='Taxes', compute='_compute_amounts')
    amount_total = fields.Monetary(string='Total', compute='_compute_amounts')
    parent_id = fields.Many2one(string='Parent Subscription Order',
                                comodel_name='subscription.order')
    end_date = fields.Datetime(string='End Date',help='Subscription ending date')
    renewal_request = fields.Boolean(string='Customer Can Renew',
                                     compute='_compute_renewal_request',
                                     store=True,
                                     help='If need to make customer to give request to renew the subscription enable '
                                          'this field')


    def _compute_invoice_count(self):
        """Compute the number of invoices associated with this subscription order."""
        for rec in self:
            rec.invoice_count = self.env['account.move'].search_count(
                [('subscription_order_id', '=', rec.id)])

    @api.depends('state_subscription', 'state')
    def _compute_recurring_revenue(self):
        """Compute the Monthly Recurring Revenue (MRR) based on active subscription lines."""
        for revenue in self:
            revenue.recurring_revenue = revenue.subscription_order_line_ids.subtotal

    def _compute_partner_street(self):
        """
        Compute the complete street address string for the partner.
        Concatenates street and street2.
        """
        for rec in self:
            street = rec.partner_id.street if rec.partner_id.street else ''
            street2 = rec.partner_id.street2 if rec.partner_id.street2 else ''
            rec.partner_street = f'{street} {street2}'

    @api.depends('sale_order_template_id')
    def _compute_renewal_request(self):
        """
        Determine if the customer is allowed to request a renewal.
        Checks the Subscription Template setting first, then falls back to the Global Setting.
        """
        global_setting = self.env['ir.config_parameter'].sudo().get_param('cyllo_subscription.renewal_request')

        for record in self:
            # Hierarchy: 1. Template (if set) -> 2. Global Setting
            if record.sale_order_template_id:
                record.renewal_request = record.sale_order_template_id.renewal_request
            else:
                record.renewal_request = global_setting

    @api.onchange('trial_end')
    def _onchange_trial_end(self):
        """Update renewal date when trial end date changes."""
        if self.trial_end:
            if self.invoice_count == 0:
                self.renewal_date = fields.Datetime.now()
            else:
                self.renewal_date = self.trial_end

    @api.depends('subscription_order_line_ids.subtotal',
                 'subscription_order_line_ids.total_price')
    def _compute_amounts(self):
        """Compute the untaxed, tax, and total amounts for the subscription order."""
        for order in self:
            amount_untaxed = sum(
                line.subtotal for line in order.subscription_order_line_ids)
            amount_total = sum(
                line.total_price for line in order.subscription_order_line_ids)
            amount_tax = amount_total - amount_untaxed
            order.update({
                'amount_untaxed': amount_untaxed,
                'amount_tax': amount_tax,
                'amount_total': amount_total,
            })

    def _compute_access_url(self):
        """Compute the portal access URL for the subscription order."""
        super()._compute_access_url()
        for request in self:
            request.access_url = f'/details/{request.id}'

    @api.model_create_multi
    def create(self, vals):
        """
        Create new subscription order records.
        Assigns a unique sequence number if the name is 'New'.
        """
        for rec in vals:
            if rec.get('name', _('New')) == _('New'):
                rec['name'] = self.env['ir.sequence'].next_by_code(
                    'subscription.order') or 'New'
        return super().create(vals)

    def unlink(self):
        """
        Delete subscription orders.
        Raises ValidationError if the order is in 'sale' or 'posted' state.
        """
        if self.state in ['sale', 'posted']:
            raise ValidationError(
                _("You cannot delete order in Sale or Posted state"))
        return super().unlink()

    def action_post(self):
        """
        Confirm the subscription order and generate the initial invoice.
        Validates the billing period and checks for existing draft invoices.
        :return: Action dictionary to view the created invoice.
        """
        if self.end_date and self.renewal_date and self.end_date < self.renewal_date:
            raise ValidationError(_("The requested billing period exceeds the current subscription duration."))
        if self.env['account.move'].search_count(
                [('invoice_origin', '=', self.name),
                 ('subscription_order_id', '=',self.id),
                 ('state', '=', 'draft')]) >= 1:
            raise ValidationError(
                _('There is already a draft invoice is present for this order, so please confirm it '
                  'or cancel it before proceed.'))

        inv = self._generate_recurring_invoice(auto_renewal=False)

        self.state = 'posted'

        if self.trial_end and self.trial_end >= self.renewal_date:
            history_exists = self.env['subscription.trial.history'].search_count([
                ('partner_id', '=', self.partner_id.id),
                ('time_based_price_id', '=', self.time_based_price_id.id)
            ], limit=1)
            if not history_exists:
                self.env['subscription.trial.history'].create({
                    'partner_id': self.partner_id.id,
                    'time_based_price_id': self.time_based_price_id.id,
                    'subscription_order_id': self.id,
                    'date_started': fields.Datetime.now(),
                    'date_trial_end': self.trial_end,
                })

        if inv:
            return {
                'name': 'Invoice',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'account.move',
                'type': 'ir.actions.act_window',
                'view_id': self.env.ref('account.view_move_form').id,
                'res_id': inv.id
            }
        return True

    def action_show_invoices(self):
        """
        Open a view to show all invoices related to this subscription order.
        :return: Action dictionary for account.move
        """
        return {
            'type': 'ir.actions.act_window',
            'name': _('Invoices'),
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'target': 'current',
            'domain': [('subscription_order_id', '=', self.id)]
        }

    def action_view_report(self):
        """Open the subscription analysis report."""
        return self.env["ir.actions.actions"]._for_xml_id(
            "cyllo_subscription.action_view_reporting")

    def action_renew_order(self):
        """
        Initiate the renewal process for the subscription.
        Checks for existing active subscriptions before proceeding.
        """
        self.ensure_one()

        if self.state != "posted":
            raise ValidationError(_("Order must be in the 'posted' state to renew."))

        active_subscription = self.env['subscription.order'].search(
            [
                ('parent_id', '=', self.id),
                ('state_subscription', '=', 'active'),
            ],
            limit=1,
        )

        if active_subscription:
            raise ValidationError(
                _("You already have an active subscription for this order.")
            )

        self.check_upsell_renewal = True
        return self.action_sub_renew_upsell()

    def action_upsell(self):
        """Initiate the upsell process for the subscription."""
        self.check_upsell_renewal = False
        return self.action_sub_renew_upsell()

    def action_sub_renew_upsell(self):
        """
        Handle the logic for both Renewal and Upsell actions.
        Creates a new subscription order based on the current one and posts it if configured.
        :return: Action dictionary to view the new subscription order.
        """
        if self.invoice_count <= 0:
            raise ValidationError(
                _("Upsell or renewal isn’t allowed for subscriptions without an invoice. "
                  "Kindly invoice the %s contract first or modify it directly.",
                  self.name))

        today = fields.Datetime.now()
        if self.invoice_count == 0:
            new_renewal_date = today
        elif self.renewal_date and self.renewal_date >= today:
            new_renewal_date = self.renewal_date
        else:
            new_renewal_date = today

        order = self.create({
            'partner_id': self.partner_id.id,
            'company_id': self.company_id.id,
            'currency_id': self.currency_id.id,
            'renewal_date': new_renewal_date,
            'parent_id':self.id,
            'sale_order_template_id': self.sale_order_template_id.id,
            'time_based_price_id': self.time_based_price_id.id,
            'sale_order_id': self.sale_order_id.id,
            'trial_end': False,
            'subscription_order_line_ids': [
                fields.Command.create({
                    'product_id': line.product_id.id,
                    'product_tmpl_id': line.product_tmpl_id.id,
                    'quantity': line.quantity,
                    'time_based_price_id': line.time_based_price_id.id,
                    'subtotal': line.subtotal,
                    'tax_ids': line.tax_ids.ids,
                    'total_price' : line.total_price
                }) for line in self.subscription_order_line_ids
            ],
        })
        if self.sale_order_template_id.invoice_creation in ['draft',
                                                            'confirmed',
                                                            'sent']:
            order.action_post()
        if self.check_upsell_renewal is True:
            order.message_post(
                body=_('Subscription order is renewed from the order %s',
                       self._get_html_link()),
                message_type='comment', subtype_xmlid='mail.mt_comment')
        else:
            order.message_post(
                body=_('Subscription order is Upsell from the order %s',
                       self._get_html_link()),
                message_type='comment', subtype_xmlid='mail.mt_comment')

        return {
            'name': 'Subscription Order',
            'view_type': 'form',
            'view_mode': 'form',
            'payment_reference': self.id,
            'res_model': 'subscription.order',
            'type': 'ir.actions.act_window',
            'view_id': self.env.ref(
                'cyllo_subscription.view_subscription_order_form').id,
            'res_id': order.id
        }

    def action_close_subscription(self):
        """Open the wizard to close the subscription."""
        return {
            'name': 'Close Reason',
            'type': 'ir.actions.act_window',
            'res_model': 'subscription.close',
            'view_mode': 'form',
            'context': {'default_subscription_order_id': self.id},
            'target': 'new',
        }


    def _get_trial_discount_invoice_line(self):
        """Return invoice line Commands for trial discounts, grouped by tax combination.

        Logic:
        - Iterates over all subscription order lines whose plan has an active trial.
        - Calculates the discount per line using ``trial_value`` (fixed flat discount)
          or ``trial_percentage`` (% of line subtotal). If both are set, ``trial_value``
          takes precedence. If neither is set, the full line subtotal is discounted.
        - Groups the computed discount amounts by their unique tax-ID frozenset.
        - Returns an empty list when no trial is currently active.

        :return: list of ``fields.Command.create(...)`` dicts ready to add to
                 ``invoice_line_ids``.
        """
        self.ensure_one()
        today = fields.Datetime.now()

        # Guard: subscription must be inside its trial window
        is_on_trial = (
            self.trial_end
            and self.trial_end > today
        )
        if not is_on_trial:
            return []

        # Determine the product to use for the discount line
        trial_discount_product = self.env.ref(
                'cyllo_subscription.product_trial_discount',
                raise_if_not_found=False,
            )
        if not trial_discount_product:
            _logger.warning(
                "Trial Discount product not found. Skipping trial discount line creation for Sale Order %s.",
                self.name,
            )
            return []


        groups = {}

        for sol in self.subscription_order_line_ids:
            plan = sol.time_based_price_id
            if not (plan and plan.trial_period > 0):
                continue

            # Compute the discount amount based on the plan's trial pricing type
            pricing_type = plan.trial_pricing_type
            if not pricing_type:
                # No trial pricing configured on this plan – skip
                continue
            line_total = sol.subtotal
            if pricing_type == 'fixed_price':
                # Customer pays trial_value; discount is the remainder
                trail_total = plan.trial_value * sol.quantity
                discount_amount = max(line_total - trail_total, 0.0)
            elif pricing_type == 'percentage_discount':
                # Percentage of the line subtotal
                discount_amount = line_total * (plan.trial_percentage / 100.0)
            else:
                discount_amount = 0.0

            if not discount_amount:
                continue

            # Group key: tax combination + discount product
            tax_key = frozenset(sol.tax_ids.ids)
            group_key = (tax_key, trial_discount_product.id)
            if group_key not in groups:
                groups[group_key] = {
                    'amount': 0.0,
                    'tax_ids': sol.tax_ids,
                    'product': trial_discount_product,
                    'plan': plan,
                }
            groups[group_key]['amount'] += discount_amount

        # ------------------------------------------------------------------ #
        # Build invoice line commands from the grouped data                   #
        # ------------------------------------------------------------------ #
        commands = []
        for group_key, data in groups.items():
            plan = data['plan']
            commands.append(fields.Command.create({
                'product_id': data['product'].id,
                'name': _(
                    'Trial Discount – %(period)s %(unit)s free trial',
                    period=plan.trial_period,
                    unit=plan.trial_unit,
                ),
                'quantity': 1,
                'price_unit': -data['amount'],
                'tax_ids': [fields.Command.set(data['tax_ids'].ids)],
            }))

        return commands

    def consolidated_invoice(self):
        """
        Create a consolidated invoice from multiple subscription orders.
        Groups orders by partner and creates a single invoice for each partner.
        :return: Action dictionary to view the created invoices.
        """
        inv_id = []
        records = self.browse(self.env.context.get('active_ids')).filtered(
            lambda o: o.state_subscription != 'churned').ids
        for key, value in groupby(self.env['subscription.order'].search_read(
                [('id', 'in', records)], ['partner_id']),
                                  key=itemgetter('partner_id')):
            lst = [val['id'] for val in value]
            orders = self.browse(lst)
            partner = []
            product = {}
            for order in orders:
                partner.append(order.partner_id.id)
                product = {
                    'key': order.subscription_order_line_ids
                }
            inv = self.env['account.move'].create({
                'partner_id': partner[0],
                'move_type': 'out_invoice',
                'currency_id': order.currency_id.id,
                'payment_reference': self.ids,
                'invoice_line_ids': [
                    (fields.Command.create({
                        'product_id': product['key'].product_id.id,
                        'price_unit': product['key'].subtotal,
                        'tax_ids': product['key'].tax_ids.ids,
                    }))],
            })
            inv_id.append(inv.id)
        return {
            'name': 'Invoice',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', inv_id)],
            'target': 'current'
        }

    def _get_report_base_filename(self):
        """Return the filename for the report in the portal."""
        self.ensure_one()
        return 'Subscription Report- %s' % self.name

    def _creation_message(self):
        """
        Generate the chatter message when a subscription is created.
        Links to the origin sale order if available.
        """
        if self.sale_order_id:
            return _("Subscription order is Created from %s",
                     self.sale_order_id._get_html_link())
        return super()._creation_message()

    def check_subscription_renewal(self):
        """
        Cron Job: Identify subscriptions due for renewal within 1 day.
        Updates state to 'renew' and sends a reminder email.
        """
        records = self.search([('renewal_date', '<=',
                                fields.Datetime.now() + relativedelta(days=1)),
                               ('state_subscription', '!=', 'churned')])
        records.state_subscription = 'renew'
        for record in records:
            body = self.env.ref(
                'cyllo_subscription.mail_template_subscription_order_due_reminder_email')
            body['email_to'] = record.partner_id.email
            body.sudo().send_mail(record.id, force_send=True)

    def check_subscription_close(self):
        """
        Cron Job: Identify and close expired subscriptions.
        Searches for records where the end date has passed.
        Updates state to 'churned' and sends a closure notification email.
        """
        records = self.search([('end_date', '<',fields.Datetime.now()),('state_subscription', '!=', 'churned')])
        if records:
            records.write({'state_subscription': 'churned'})
            for record in records:
                body = self.env.ref(
                    'cyllo_subscription.mail_template_subscription_order_closed_reminder_email')
                body['email_to'] = record.partner_id.email
                body.sudo().send_mail(record.id, force_send=True)
                record.message_post(
                    body=_('Subscription order has been closed.'),
                    message_type='comment', subtype_xmlid='mail.mt_comment')

    @api.model
    def _cron_auto_generate_invoices(self):
        """Daily cron: find active subscriptions due for renewal, create a
        recurring invoice with billing period info on each line, and advance
        renewal_date by one billing cycle.
        """
        today = fields.Datetime.now()

        due_subscriptions = self.search([
            ('state_subscription', 'in', ['active', 'renew']),
            ('state', '=', 'posted'),
            ('renewal_date', '<=', today),
        ])

        _logger.info(
            "Auto-Invoice Cron: found %d subscription(s) due for renewal.",
            len(due_subscriptions)
        )

        invoice_count = 0
        for order in due_subscriptions:
            if order.trial_end and order.trial_end > today:
                _logger.info(
                    "Skipping %s – still in trial until %s.",
                    order.name, order.trial_end
                )
                continue

            existing_draft = self.env['account.move'].search_count([
                ('invoice_origin', '=', order.name),
                ('is_subscription', '=', True),
                ('state', '=', 'draft'),
            ])
            if existing_draft:
                _logger.info(
                    "Skipping %s – draft invoice already exists.",
                    order.name
                )
                continue

            try:
                inv = order._generate_recurring_invoice(auto_renewal=True)
                if inv:
                    invoice_count += 1
            except Exception:
                _logger.exception(
                    "Error generating recurring invoice for subscription %s.",
                    order.name
                )

        _logger.info(
            "Auto-Invoice Cron: generated %d recurring invoice(s).",
            invoice_count
        )

    def _generate_recurring_invoice(self,auto_renewal):
        """Create one recurring invoice for this subscription.
        """
        self.ensure_one()

        tbp = self.time_based_price_id
        if not self.subscription_order_line_ids or not tbp or not tbp.subscription_unit or not tbp.duration:
            return False

        subscription_unit = tbp.subscription_unit
        duration = tbp.duration
        delta = relativedelta(**{subscription_unit: duration})
        if not self.trial_end:
            self.trial_end = fields.datetime.today()
        if self.renewal_date <= self.trial_end and self.invoice_count == 0:
            period_start = self.trial_end - relativedelta(**{tbp.trial_unit: tbp.trial_period})
            period_end = self.trial_end
            new_renewal_date = period_end
            duration_label="Trial"
        else:
            period_start = self.renewal_date
            period_end = period_start + delta - relativedelta(days=1)
            new_renewal_date = period_start + delta
            unit_map = {
                'weeks': (_('1 Week'), _('%s Weeks')),
                'months': (_('1 Month'), _('%s Months')),
                'years': (_('1 Year'), _('%s Years')),
            }
            singular, plural = unit_map.get(
                subscription_unit, (subscription_unit, subscription_unit)
            )
            duration_label = singular if duration == 1 else (plural % duration)
        period_start_date = (
            period_start.date() if hasattr(period_start, 'date') else period_start
        )
        period_end_date = (
            period_end.date() if hasattr(period_end, 'date') else period_end
        )
        lang_code = self.partner_id.lang
        format_start = format_date(self.env, period_start_date, lang_code=lang_code)
        format_end = format_date(self.env, period_end_date, lang_code=lang_code)
        start_to_end = _('%(start)s to %(next)s', start=format_start, next=format_end)


        invoice_line_ids = []
        for line in self.subscription_order_line_ids:
            product_name = line.product_id.with_context(
                lang=lang_code).display_name
            description = f"{product_name}\n{duration_label} {start_to_end}"
            price = line.subtotal/line.quantity
            invoice_line_ids.append(fields.Command.create({
                'product_id': line.product_id.id,
                'name': description,
                'quantity': line.quantity if line.quantity else 1,
                'price_unit': price,
                'tax_ids': [fields.Command.set(line.tax_ids.ids)],
                'sale_line_ids': [fields.Command.set([line.sale_order_line_id.id])] if line.sale_order_line_id else [],
            }))
        if self.renewal_date <= self.trial_end and self.invoice_count == 0:
                discount_line = self._get_trial_discount_invoice_line()
                if discount_line:
                    invoice_line_ids.extend(discount_line)


        inv = self.env['account.move'].create({
            'partner_id': self.partner_id.id,
            'move_type': 'out_invoice',
            'payment_reference': self.name,
            'invoice_origin': f"{self.sale_order_id.name} - {self.name}" if self.sale_order_id else self.name,
            'invoice_date': fields.Date.today(),
            'invoice_date_due': new_renewal_date,
            'renewal_date': new_renewal_date,
            'date': fields.Datetime.now(),
            'is_subscription': True,
            'is_auto_renewal': auto_renewal,
            'subscription_order_id': self.id,
            'trial_period': f'{tbp.trial_period} {tbp.trial_unit}',
            'invoice_line_ids': invoice_line_ids,
        })

        self.account_move_ids = [(4, inv.id)]

        invoice_creation = (
            self.sale_order_template_id.invoice_creation
            if self.sale_order_template_id
            else 'manually'
        )
        if invoice_creation == 'confirmed':
            inv.action_post()
            self._handle_automated_payment(inv)
        elif invoice_creation == 'sent':
            inv.action_post()
            self._handle_automated_payment(inv)
            mail_template = (
                self.sale_order_template_id.subscription_mail_template_id
            )
            if mail_template:
                mail_template.sudo().send_mail(
                    inv.id, force_send=True,
                    email_values={'email_to': self.partner_id.email},
                )

        return inv

    def _handle_automated_payment(self, invoice):
        """If the subscription has a payment token, attempt to charge it
        automatically, but only for recurring invoices (not the initial checkout).
        """
        # Prevent double charging the initial invoice which was paid at checkout
        if not invoice.is_auto_renewal:
            return

        token = self.sale_order_id.payment_token_id
        
        if token and invoice.state == 'posted' and invoice.payment_state not in ['paid', 'in_payment']:
            try:
                self._do_payment(token, invoice)
            except Exception as e:
                invoice._message_log(body=_("Automated payment collection failed: %s", str(e)))

    def _do_payment(self, payment_token, invoice):
        """Create a payment transaction and charge the token,
        mirroring native Odoo behavior."""
        values = [{
            'provider_id': payment_token.provider_id.id,
            'payment_method_id': payment_token.payment_method_id.id,
            'amount': invoice.amount_total,
            'currency_id': invoice.currency_id.id,
            'partner_id': invoice.partner_id.id,
            'token_id': payment_token.id,
            'operation': 'offline',
            'invoice_ids': [fields.Command.set(invoice.ids)],
            'reference': self.env['payment.transaction']._compute_reference(
                payment_token.provider_id.code, prefix=invoice.name
            ),
        }]
        transactions_sudo = self.env['payment.transaction'].sudo().create(values)
        for tx_sudo in transactions_sudo:
            self.env.cr.execute(
                "SELECT 1 FROM payment_transaction WHERE id=%s FOR NO KEY UPDATE",
                [tx_sudo.id]
            )
            tx_sudo._send_payment_request()
        return transactions_sudo
