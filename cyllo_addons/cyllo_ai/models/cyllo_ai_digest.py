# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cyllo(<https://www.cyllo.com>)
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
"""What happened in a period: one compact digest across the installed apps.

Each metric is a count (and, where it makes sense, a total) of the documents
an app finished in the period, read as the current user so record rules
apply. Only counts, totals and links are returned, never record rows, which
keeps the agent's token use small. Each metric carries a short
``/web#cyllo_digest=...`` link that the chat turns into the filtered list.
"""
from datetime import datetime, time, timedelta

import pytz

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.tools.misc import format_amount, format_date
from odoo.tools.translate import _lt

MAX_DAYS = 400

DIGEST_METRICS = [
    {'key': 'sale_quotes', 'app': _lt("Sales"), 'label': _lt("Quotations created"),
     'model': 'sale.order', 'date': 'create_date', 'domain': []},
    {'key': 'sale_orders', 'app': _lt("Sales"), 'label': _lt("Sales orders confirmed"),
     'model': 'sale.order', 'date': 'date_order', 'domain': [('state', '=', 'sale')],
     'amount': 'amount_total', 'convert': True},
    {'key': 'pos_orders', 'app': _lt("Point of Sale"), 'label': _lt("POS orders"),
     'model': 'pos.order', 'date': 'date_order',
     'domain': [('state', 'in', ('paid', 'done', 'invoiced'))],
     'amount': 'amount_total', 'convert': True},
    {'key': 'invoices', 'app': _lt("Invoicing"), 'label': _lt("Customer invoices posted"),
     'model': 'account.move', 'date': 'invoice_date',
     'domain': [('move_type', '=', 'out_invoice'), ('state', '=', 'posted')],
     'amount': 'amount_total_signed'},
    {'key': 'payments_in', 'app': _lt("Invoicing"), 'label': _lt("Payments received"),
     'model': 'account.payment', 'date': 'date',
     'domain': [('payment_type', '=', 'inbound'), ('state', '=', 'posted')],
     'amount': 'amount_company_currency_signed'},
    {'key': 'bills', 'app': _lt("Invoicing"), 'label': _lt("Vendor bills posted"),
     'model': 'account.move', 'date': 'invoice_date',
     'domain': [('move_type', '=', 'in_invoice'), ('state', '=', 'posted')],
     'amount': 'amount_total_signed'},
    {'key': 'payments_out', 'app': _lt("Invoicing"), 'label': _lt("Payments made"),
     'model': 'account.payment', 'date': 'date',
     'domain': [('payment_type', '=', 'outbound'), ('state', '=', 'posted')],
     'amount': 'amount_company_currency_signed'},
    {'key': 'purchase_orders', 'app': _lt("Purchase"), 'label': _lt("Purchase orders confirmed"),
     'model': 'purchase.order', 'date': 'date_order',
     'domain': [('state', 'in', ('purchase', 'done'))],
     'amount': 'amount_total', 'convert': True},
    {'key': 'leads_new', 'app': _lt("CRM"), 'label': _lt("Leads created"),
     'model': 'crm.lead', 'date': 'create_date',
     'domain': ['|', ('type', '=', 'lead'), ('type', '=', False)]},
    {'key': 'opportunities_new', 'app': _lt("CRM"), 'label': _lt("Opportunities created"),
     'model': 'crm.lead', 'date': 'create_date', 'domain': [('type', '=', 'opportunity')]},
    {'key': 'leads_won', 'app': _lt("CRM"), 'label': _lt("Opportunities won"),
     'model': 'crm.lead', 'date': 'date_closed', 'domain': [('stage_id.is_won', '=', True)],
     'amount': 'expected_revenue'},
    {'key': 'receipts', 'app': _lt("Inventory"), 'label': _lt("Receipts done"),
     'model': 'stock.picking', 'date': 'date_done',
     'domain': [('state', '=', 'done'), ('picking_type_code', '=', 'incoming')]},
    {'key': 'deliveries', 'app': _lt("Inventory"), 'label': _lt("Deliveries done"),
     'model': 'stock.picking', 'date': 'date_done',
     'domain': [('state', '=', 'done'), ('picking_type_code', '=', 'outgoing')]},
    {'key': 'mo_done', 'app': _lt("Manufacturing"), 'label': _lt("Manufacturing orders done"),
     'model': 'mrp.production', 'date': 'date_finished', 'domain': [('state', '=', 'done')]},
    {'key': 'tasks_new', 'app': _lt("Project"), 'label': _lt("Tasks created"),
     'model': 'project.task', 'date': 'create_date', 'domain': []},
    {'key': 'tasks_done', 'app': _lt("Project"), 'label': _lt("Tasks completed"),
     'model': 'project.task', 'date': 'date_last_stage_update', 'domain': [('state', '=', '1_done')]},
    {'key': 'tickets_new', 'app': _lt("Helpdesk"), 'label': _lt("Tickets opened"),
     'model': 'helpdesk.ticket', 'date': 'create_date', 'domain': []},
    {'key': 'tickets_closed', 'app': _lt("Helpdesk"), 'label': _lt("Tickets closed"),
     'model': 'helpdesk.ticket', 'date': 'closed_date', 'domain': []},
    {'key': 'employees_new', 'app': _lt("Employees"), 'label': _lt("New employees"),
     'model': 'hr.employee', 'date': 'create_date', 'domain': []},
    {'key': 'leaves', 'app': _lt("Time Off"), 'label': _lt("Time off approved"),
     'model': 'hr.leave', 'date': 'date_from', 'domain': [('state', '=', 'validate')]},
    {'key': 'activities_done', 'app': _lt("Activities"), 'label': _lt("Activities completed"),
     'model': 'mail.message', 'date': 'date', 'domain': [('mail_activity_type_id', '!=', False)]},
]

ANSWER_STYLE = (
    "Give an overall summary only, no tables and no per-record details: one short "
    "headline sentence for the period, then one bullet per app with its key numbers "
    "(mention the change vs the previous period when it is notable) and a "
    "[View](link) link copied exactly from the result, then at most one sentence on "
    "what stands out. Do not call other tools unless the user asks for more detail."
)


class CylloAiDigest(models.AbstractModel):
    _name = 'cyllo.ai.digest'
    _description = 'Cyllo AI Activity Digest'

    @api.model
    def get_digest(self, date_from, date_to, company_ids=None):
        """Counts and totals per installed app for ``date_from``..``date_to``.

        Also counts the previous period of the same length, so the summary can
        say what changed. Apps the user cannot read are left out.
        """
        self._check_ai_user()
        start, end = self._parse_period(date_from, date_to)
        env_self = self._scoped(company_ids)
        span = (end - start).days + 1
        prev_start, prev_end = start - timedelta(days=span), start - timedelta(days=1)
        currency = env_self.env.company.currency_id
        apps = {}
        for spec in env_self._available_metrics():
            count, amount = env_self._measure(spec, start, end)
            if not count:
                continue
            prev_count, __ = env_self._measure(spec, prev_start, prev_end, with_amount=False)
            item = {'what': str(spec['label']), 'count': count, 'prev': prev_count,
                    'link': self._link(spec['key'], start, end)}
            if amount is not None:
                item['amount'] = format_amount(self.env, abs(amount), currency)
            apps.setdefault(str(spec['app']), []).append(item)
        return {
            'period': "%s – %s" % (format_date(self.env, start), format_date(self.env, end)),
            'previous_period': "%s – %s" % (format_date(self.env, prev_start),
                                            format_date(self.env, prev_end)),
            'currency': currency.name,
            'amounts': 'tax included, in company currency',
            'apps': apps or _("Nothing was recorded in this period."),
            'answer_style': ANSWER_STYLE,
        }

    @api.model
    def get_metric_action(self, key, date_from, date_to):
        """Window action listing the records behind one digest metric."""
        self._check_ai_user()
        spec = next((m for m in self._available_metrics() if m['key'] == key), None)
        if not spec:
            raise UserError(_("This summary link is no longer available."))
        start, end = self._parse_period(date_from, date_to)
        return {
            'type': 'ir.actions.act_window',
            'name': "%s · %s – %s" % (spec['label'], format_date(self.env, start),
                                       format_date(self.env, end)),
            'res_model': spec['model'],
            'domain': self._domain(spec, start, end),
            'views': [[False, 'list'], [False, 'form']],
            'context': {'create': False},
            'target': 'current',
        }

    def _check_ai_user(self):
        """Refuse callers outside the Cyllo AI user group (e.g. portal users)."""
        if not self.env.user.has_group('cyllo_ai.group_cyllo_ai_user'):
            raise AccessError(_("The activity summary is only available to Cyllo AI users."))

    def _available_metrics(self):
        """Metrics whose app is installed, readable and has the expected fields."""
        metrics = []
        for spec in DIGEST_METRICS:
            if spec['model'] not in self.env:
                continue
            Model = self.env[spec['model']]
            needed = [spec['date']] + [leaf[0].split('.')[0] for leaf in spec['domain']
                                       if isinstance(leaf, (tuple, list))]
            if spec.get('amount'):
                needed.append(spec['amount'])
            if any(name not in Model._fields for name in needed):
                continue
            if not Model.check_access_rights('read', raise_exception=False):
                continue
            metrics.append(spec)
        return metrics

    def _measure(self, spec, start, end, with_amount=True):
        """Return ``(count, amount)`` of one metric; amount is in company currency."""
        Model = self.env[spec['model']]
        domain = self._domain(spec, start, end)
        amount_field = spec.get('amount') if with_amount else None
        if not amount_field:
            return Model.search_count(domain), None
        currency_field = getattr(Model._fields[amount_field], 'currency_field', None) or 'currency_id'
        if spec.get('convert') and currency_field in Model._fields \
                and Model._fields[currency_field].store:
            company = self.env.company
            count = amount = 0
            groups = Model._read_group(domain, [currency_field], ['__count', amount_field + ':sum'])
            for currency, group_count, total in groups:
                count += group_count
                amount += currency._convert(total or 0.0, company.currency_id, company, end) \
                    if currency and currency != company.currency_id else (total or 0.0)
            return count, amount
        [(count, amount)] = Model._read_group(domain, [], ['__count', amount_field + ':sum'])
        return count, amount or 0.0

    def _domain(self, spec, start, end):
        """Metric domain restricted to the period in the user's timezone."""
        field = self.env[spec['model']]._fields[spec['date']]
        if field.type == 'datetime':
            tz = pytz.timezone(self.env.user.tz or 'UTC')
            low = tz.localize(datetime.combine(start, time.min)).astimezone(pytz.utc)
            high = tz.localize(datetime.combine(end + timedelta(days=1), time.min)).astimezone(pytz.utc)
            period = [(spec['date'], '>=', fields.Datetime.to_string(low.replace(tzinfo=None))),
                      (spec['date'], '<', fields.Datetime.to_string(high.replace(tzinfo=None)))]
        else:
            period = [(spec['date'], '>=', fields.Date.to_string(start)),
                      (spec['date'], '<=', fields.Date.to_string(end))]
        return list(spec['domain']) + period

    def _scoped(self, company_ids):
        """Self restricted to the companies selected in the chat, if any."""
        allowed = [cid for cid in (company_ids or []) if cid in self.env.user.company_ids.ids]
        if not allowed:
            return self
        return self.with_context(allowed_company_ids=allowed).with_company(allowed[0])

    @staticmethod
    def _parse_period(date_from, date_to):
        """Validate the period and return it as two dates."""
        try:
            start = fields.Date.to_date(date_from)
            end = fields.Date.to_date(date_to)
        except (TypeError, ValueError):
            raise UserError(_("Dates must be given as YYYY-MM-DD."))
        if not start or not end:
            raise UserError(_("Both a start and an end date are required."))
        if end < start:
            start, end = end, start
        if (end - start).days > MAX_DAYS:
            raise UserError(_("The period is too long; use at most %s days.", MAX_DAYS))
        return start, end

    @staticmethod
    def _link(key, start, end):
        """Short chat link that opens the records behind a metric."""
        return "/web#cyllo_digest=%s&from=%s&to=%s" % (key, start.isoformat(), end.isoformat())
