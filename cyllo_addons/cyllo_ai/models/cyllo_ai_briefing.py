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
"""Catch me up: a one-click briefing on a customer, vendor, lead or project.

Facts are collected deterministically through the ORM as the current user, so
the briefing only ever shows what that user may read, and every figure carries
the record (or list) it came from. The configured LLM only turns those facts
into a short narrative and a suggested next step; when it is unavailable a
rule-based narrative is returned instead.
"""
import json
import logging
import re
from datetime import date, datetime, timedelta

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.osv import expression
from odoo.tools import html2plaintext
from odoo.tools.misc import format_amount, format_date

from ..core.llm_client import LLMClient

_logger = logging.getLogger(__name__)

BRIEFING_MODELS = ('res.partner', 'crm.lead', 'project.project')
LIST_LIMIT = 5
MESSAGE_DAYS = 60
EXCERPT_CHARS = 400
TICKET_WAIT_DAYS = 3
STALE_STAGE_DAYS = 14
QUIET_DAYS = 14
SALES_DROP_PCT = 20
SALES_DROP_HIGH_PCT = 40
OVERDUE_HIGH_DAYS = 30
TASK_CLOSED_STATES = ('1_done', '1_canceled')
SEVERITY_ORDER = {'high': 0, 'medium': 1}

NARRATIVE_PROMPT = """You prepare a busy {role} for a conversation about one \
business record in an ERP. You receive the facts as JSON.

Write the briefing in {lang}:
- Use ONLY the facts given. Never invent figures, dates, names or events.
- Start with the risks (overdue money, an unhappy customer, falling orders, \
late work), then the other useful context such as what they recently asked for.
- 3 to 6 short sentences of plain text. No markdown, no headings, no bullets.
- Write money compactly the way it is read in the currency's region, e.g. \
for Indian rupees use lakh and crore (₹4.1 L, ₹1.2 Cr).
- Judge the mood of the other party only from their messages and tickets.

Reply with JSON only, no code fences:
{{"summary": "...", "next_step": "one concrete action, in the imperative", \
"mood": "positive|neutral|negative|unknown", "mood_reason": "short reason or empty"}}"""


class CylloAiBriefing(models.AbstractModel):
    _name = 'cyllo.ai.briefing'
    _description = 'Cyllo AI Catch Me Up Briefing'

    @api.model
    def get_briefing(self, res_model, res_id):
        """Build the Catch me up briefing for one record.

        :return: dict with ``title``, ``subtitle``, ``kpis``, ``risks``,
                 ``sections``, ``summary``, ``next_step``, ``mood``,
                 ``mood_reason``, ``source`` ('ai' or 'rules') and ``notice``.
        """
        if not self.env.user.has_group('cyllo_ai.group_cyllo_ai_user'):
            raise AccessError(_("Catch me up is only available to Cyllo AI users."))
        if res_model not in BRIEFING_MODELS or res_model not in self.env:
            raise UserError(_("Catch me up is not available for this record."))
        record = self.env[res_model].browse(int(res_id)).exists()
        if not record:
            raise UserError(_("This record no longer exists."))
        record.check_access_rights('read')
        record.check_access_rule('read')

        brief = {'kpis': [], 'risks': [], 'sections': []}
        today = fields.Date.context_today(self)
        builders = {
            'res.partner': self._build_partner,
            'crm.lead': self._build_lead,
            'project.project': self._build_project,
        }
        brief.update(builders[res_model](record, today, brief))
        brief['risks'].sort(key=lambda r: SEVERITY_ORDER.get(r['severity'], 9))
        brief.update(self._narrative(brief, today))
        brief['generated_at'] = fields.Datetime.to_string(fields.Datetime.now())
        return brief

    # -- record builders ------------------------------------------------------

    def _build_partner(self, record, today, brief):
        """Customer / vendor briefing on the commercial entity of ``record``."""
        partner = record.commercial_partner_id
        roles = []
        if self._safe(self._add_sales, partner, today, brief):
            roles.append(_("Customer"))
        if self._safe(self._add_purchases, partner, today, brief):
            roles.append(_("Vendor"))
        self._safe(self._add_invoices, partner, today, brief, 'out')
        self._safe(self._add_invoices, partner, today, brief, 'in')
        tickets = self._safe(self._add_tickets, partner, today, brief) or []
        leads = self._safe(self._add_opportunities, partner, brief) or []
        family = self._family(partner)
        self._safe(self._add_messages, brief, today,
                   [('author_id', 'in', family.ids)], _("Recent messages from them"))
        targets = [('res.partner', family.ids), ('crm.lead', leads),
                   ('helpdesk.ticket', tickets)]
        self._safe(self._add_activities, targets, today, brief)
        if not roles:
            roles.append(_("Contact"))
        return {'title': partner.display_name, 'subtitle': " & ".join(roles),
                'role': 'sales or purchase manager'}

    def _build_lead(self, lead, today, brief):
        """Lead / opportunity briefing, plus the partner's money and tickets."""
        currency = lead.company_currency or self.env.company.currency_id
        stage_days = self._days_since(lead.date_last_stage_update, today)
        brief['kpis'].append(self._kpi(
            'expected', _("Expected revenue"), self._money(lead.expected_revenue, currency),
            _("%(prob)s %% probability · %(stage)s",
              prob=round(lead.probability or 0), stage=lead.stage_id.name or _("No stage")),
            'muted', 'crm.lead', res_id=lead.id))
        if stage_days is not None:
            brief['kpis'].append(self._kpi(
                'stage_days', _("In this stage"), _("%s days", stage_days),
                _("Since %s", self._fmt_date(lead.date_last_stage_update)),
                'warning' if stage_days > STALE_STAGE_DAYS else 'muted',
                'crm.lead', res_id=lead.id))
        if lead.date_deadline and lead.date_deadline < today and lead.probability < 100:
            late = (today - lead.date_deadline).days
            self._risk(brief, 'high', _(
                "The expected closing date (%(date)s) passed %(days)s days ago.",
                date=self._fmt_date(lead.date_deadline), days=late),
                _("Agree a new closing date with the customer and update the opportunity."),
                'crm.lead', res_id=lead.id)
        if stage_days is not None and stage_days > STALE_STAGE_DAYS and lead.probability < 100:
            self._risk(brief, 'medium', _(
                "It has been in %(stage)s for %(days)s days without moving.",
                stage=lead.stage_id.name or _("the same stage"), days=stage_days),
                _("Find out what is blocking the decision and agree the next step."),
                'crm.lead', res_id=lead.id)

        last_message = self._safe(self._add_messages, brief, today,
                                  [('model', '=', 'crm.lead'), ('res_id', '=', lead.id)],
                                  _("Conversation on this lead"))
        if last_message:
            quiet = (today - last_message).days
            if quiet > QUIET_DAYS and lead.probability < 100:
                self._risk(brief, 'medium', _(
                    "No messages have been exchanged for %s days.", quiet),
                    _("Reach out today so the opportunity does not go cold."),
                    'crm.lead', res_id=lead.id)
        pending = self._safe(self._add_activities, [('crm.lead', [lead.id])], today, brief)
        if pending == 0 and lead.probability < 100 and lead.active:
            self._risk(brief, 'medium', _("Nothing is scheduled as the next step."),
                       _("Schedule the next activity before the call ends."),
                       'crm.lead', res_id=lead.id)

        partner = lead.partner_id.commercial_partner_id
        if partner:
            self._safe(self._add_sales, partner, today, brief)
            self._safe(self._add_invoices, partner, today, brief, 'out')
            self._safe(self._add_tickets, partner, today, brief)
        kind = _("Opportunity") if lead.type == 'opportunity' else _("Lead")
        subtitle = " · ".join(filter(None, [kind, partner.display_name if partner else
                                            lead.contact_name or lead.partner_name]))
        return {'title': lead.name, 'subtitle': subtitle, 'role': 'salesperson'}

    def _build_project(self, project, today, brief):
        """Project briefing: deadlines, late tasks, budget, status and client."""
        Task = self.env['project.task']
        task_ids = []
        if Task.check_access_rights('read', raise_exception=False):
            task_ids = self._safe(self._add_tasks, project, today, brief) or []

        if 'last_update_status' in project._fields and \
                project.last_update_status in ('at_risk', 'off_track'):
            label = dict(project._fields['last_update_status']._description_selection(
                self.env)).get(project.last_update_status)
            self._risk(brief, 'high' if project.last_update_status == 'off_track' else 'medium',
                       _("The last project update marked it %s.", label),
                       _("Review the last update with the project manager and agree recovery steps."),
                       'project.project', res_id=project.id)
        if project.date:
            days_left = (project.date - today).days
            brief['kpis'].append(self._kpi(
                'deadline', _("Deadline"), self._fmt_date(project.date),
                _("%s days left", days_left) if days_left >= 0
                else _("%s days late", -days_left),
                'danger' if days_left < 0 else 'warning' if days_left <= 7 else 'muted',
                'project.project', res_id=project.id))
        if {'allocated_hours', 'effective_hours'} <= set(project._fields) and project.allocated_hours:
            used = project.effective_hours / project.allocated_hours * 100
            brief['kpis'].append(self._kpi(
                'hours', _("Hours used"), "%d %%" % round(used),
                _("%(spent)s h of %(budget)s h",
                  spent=round(project.effective_hours, 1), budget=round(project.allocated_hours, 1)),
                'danger' if used > 100 else 'warning' if used > 85 else 'muted',
                'project.project', res_id=project.id))
            if used > 100:
                self._risk(brief, 'medium', _(
                    "Hours spent are over budget: %(spent)s h of %(budget)s h.",
                    spent=round(project.effective_hours, 1), budget=round(project.allocated_hours, 1)),
                    _("Discuss the extra effort with the client before more hours are logged."),
                    'project.project', res_id=project.id)

        message_domain = expression.OR([
            [('model', '=', 'project.project'), ('res_id', '=', project.id)],
            [('model', '=', 'project.task'), ('res_id', 'in', task_ids)],
        ])
        self._safe(self._add_messages, brief, today, message_domain, _("Recent conversation"))
        self._safe(self._add_activities,
                   [('project.project', [project.id]), ('project.task', task_ids)], today, brief)

        partner = project.partner_id.commercial_partner_id
        if partner:
            self._safe(self._add_invoices, partner, today, brief, 'out')
            self._safe(self._add_tickets, partner, today, brief)
        subtitle = " · ".join(filter(None, [_("Project"), partner.display_name if partner else '',
                                            project.user_id.name]))
        return {'title': project.name, 'subtitle': subtitle, 'role': 'project manager'}

    # -- fact blocks ----------------------------------------------------------

    def _add_sales(self, partner, today, brief):
        """Quarter-to-date sales against the same point of last quarter."""
        if not self._can_read('sale.order'):
            return False
        q_start = date(today.year, 3 * ((today.month - 1) // 3) + 1, 1)
        prev_start = q_start - relativedelta(months=3)
        prev_same = prev_start + timedelta(days=(today - q_start).days)
        orders = self.env['sale.order'].search([
            ('partner_id', 'child_of', partner.id), ('state', '=', 'sale'),
            ('date_order', '>=', fields.Datetime.to_datetime(prev_start)),
        ], order='date_order desc')
        this_q = last_same = last_total = 0.0
        for order in orders:
            day = order.date_order.date()
            amount = self._to_company(order.amount_untaxed, order.currency_id,
                                      order.company_id, day)
            if day >= q_start:
                this_q += amount
            else:
                last_total += amount
                if day <= prev_same:
                    last_same += amount
        if not orders and not partner.customer_rank:
            return False

        hint = _("Last quarter in total: %s", self._money(last_total))
        tone = 'muted'
        if last_same:
            change = (this_q - last_same) / last_same * 100
            hint = _("%(sign)s%(pct)s %% vs %(prev)s at this point last quarter",
                     sign='+' if change >= 0 else '−', pct=abs(round(change)),
                     prev=self._money(last_same))
            if change <= -SALES_DROP_PCT:
                tone = 'danger'
                self._risk(brief, 'high' if change <= -SALES_DROP_HIGH_PCT else 'medium', _(
                    "Orders are down %(pct)s %% this quarter (%(now)s vs %(prev)s at the same "
                    "point last quarter).", pct=abs(round(change)), now=self._money(this_q),
                    prev=self._money(last_same)),
                    _("Ask what has changed in their demand and offer something to win the volume back."),
                    'sale.order', domain=[('partner_id', 'child_of', partner.id), ('state', '=', 'sale')],
                    name=_("Sales orders"))
            elif change >= SALES_DROP_PCT:
                tone = 'success'
        brief['kpis'].append(self._kpi(
            'sales', _("Sales this quarter"), self._money(this_q), hint, tone, 'sale.order',
            domain=[('partner_id', 'child_of', partner.id), ('state', '=', 'sale')],
            name=_("Sales orders")))
        if orders:
            brief['sections'].append(self._section('orders', _("Recent orders"), [
                self._row(o.name, self._fmt_date(o.date_order),
                          self._money(o.amount_total, o.currency_id), 'muted', 'sale.order', o.id)
                for o in orders[:3]]))
        return True

    def _add_purchases(self, partner, today, brief):
        """Purchases from a vendor this quarter and open purchase orders."""
        if 'purchase.order' not in self.env or not self._can_read('purchase.order'):
            return False
        q_start = date(today.year, 3 * ((today.month - 1) // 3) + 1, 1)
        orders = self.env['purchase.order'].search([
            ('partner_id', 'child_of', partner.id), ('state', 'in', ('purchase', 'done')),
            ('date_approve', '>=', fields.Datetime.to_datetime(q_start)),
        ])
        if not orders and not partner.supplier_rank:
            return False
        total = sum(self._to_company(o.amount_untaxed, o.currency_id, o.company_id,
                                     (o.date_approve or o.date_order).date()) for o in orders)
        late = self.env['purchase.order'].search([
            ('partner_id', 'child_of', partner.id), ('state', '=', 'purchase'),
            ('receipt_status', 'in', ('pending', 'partial')),
            ('date_planned', '<', fields.Datetime.to_datetime(today)),
        ], order='date_planned asc') if 'receipt_status' in self.env['purchase.order']._fields \
            else self.env['purchase.order']
        brief['kpis'].append(self._kpi(
            'purchases', _("Purchased this quarter"), self._money(total),
            _("%s orders", len(orders)), 'muted', 'purchase.order',
            domain=[('partner_id', 'child_of', partner.id), ('state', 'in', ('purchase', 'done'))],
            name=_("Purchase orders")))
        if late:
            oldest = (today - late[0].date_planned.date()).days
            self._risk(brief, 'medium', _(
                "%(count)s purchase orders are late for delivery, the oldest by %(days)s days.",
                count=len(late), days=oldest),
                _("Ask for a firm delivery date on the late purchase orders."),
                'purchase.order', domain=[('id', 'in', late.ids)], name=_("Late purchase orders"))
            brief['sections'].append(self._section('late_po', _("Late deliveries"), [
                self._row(o.name, _("Expected %(date)s · %(days)s days late",
                                    date=self._fmt_date(o.date_planned),
                                    days=(today - o.date_planned.date()).days),
                          self._money(o.amount_total, o.currency_id), 'danger',
                          'purchase.order', o.id)
                for o in late[:LIST_LIMIT]]))
        return True

    def _add_invoices(self, partner, today, brief, direction):
        """Unpaid customer invoices (``out``) or vendor bills (``in``)."""
        if not self._can_read('account.move'):
            return
        move_type = 'out_invoice' if direction == 'out' else 'in_invoice'
        domain = [('commercial_partner_id', '=', partner.id), ('state', '=', 'posted'),
                  ('move_type', '=', move_type), ('payment_state', 'in', ('not_paid', 'partial'))]
        moves = self.env['account.move'].search(domain, order='invoice_date_due asc, id asc')
        if not moves:
            return
        overdue = moves.filtered(lambda m: (m.invoice_date_due or m.invoice_date or today) < today)
        unpaid_total = sum(abs(m.amount_residual_signed) for m in moves)
        overdue_total = sum(abs(m.amount_residual_signed) for m in overdue)
        oldest = (today - (overdue[0].invoice_date_due or overdue[0].invoice_date)).days \
            if overdue else 0
        is_out = direction == 'out'
        list_name = _("Unpaid invoices") if is_out else _("Unpaid bills")
        brief['kpis'].append(self._kpi(
            'receivable' if is_out else 'payable',
            _("They owe us") if is_out else _("We owe them"), self._money(unpaid_total),
            _("%(count)s overdue (%(amount)s), oldest %(days)s days",
              count=len(overdue), amount=self._money(overdue_total), days=oldest)
            if overdue else _("%s unpaid, none overdue", len(moves)),
            ('danger' if is_out else 'warning') if overdue else 'muted',
            'account.move', domain=domain, name=list_name))
        if overdue:
            if is_out:
                self._risk(brief, 'high' if oldest > OVERDUE_HIGH_DAYS else 'medium', _(
                    "%(count)s invoices are overdue, total %(amount)s, the oldest %(days)s days.",
                    count=len(overdue), amount=self._money(overdue_total), days=oldest),
                    _("Ask for a payment date on the overdue invoices."),
                    'account.move', domain=[('id', 'in', overdue.ids)], name=_("Overdue invoices"))
            else:
                self._risk(brief, 'medium', _(
                    "We have %(count)s overdue bills to them, total %(amount)s, the oldest "
                    "%(days)s days.", count=len(overdue), amount=self._money(overdue_total),
                    days=oldest),
                    _("Check the overdue bills with accounts before the call."),
                    'account.move', domain=[('id', 'in', overdue.ids)], name=_("Overdue bills"))
        rows = []
        for move in moves[:LIST_LIMIT]:
            due = move.invoice_date_due or move.invoice_date
            late = (today - due).days if due else 0
            rows.append(self._row(
                move.name,
                _("Due %(date)s · %(days)s days overdue", date=self._fmt_date(due), days=late)
                if late > 0 else _("Due %s", self._fmt_date(due)),
                self._money(abs(move.amount_residual_signed)),
                'danger' if late > 0 else 'muted', 'account.move', move.id))
        brief['sections'].append(self._section(
            'invoices_' + direction, list_name, rows,
            self._list_action('account.move', domain, list_name) if len(moves) > LIST_LIMIT else None))

    def _add_tickets(self, partner, today, brief):
        """Open helpdesk tickets of the partner; returns their ids."""
        if 'helpdesk.ticket' not in self.env or not self._can_read('helpdesk.ticket'):
            return []
        Ticket = self.env['helpdesk.ticket']
        domain = [('customer_id', 'child_of', partner.id)]
        if 'is_closed' in self.env['helpdesk.stage']._fields:
            domain.append(('stage_id.is_closed', '=', False))
        tickets = Ticket.search(domain, order='date asc, id asc')
        if not tickets:
            return []
        rows = []
        worst = None
        for ticket in tickets:
            waited = self._days_since(ticket.date or ticket.create_date, today) or 0
            urgent = waited >= TICKET_WAIT_DAYS or ticket.sla_failed or ticket.priority in ('2', '3')
            if urgent and (worst is None or waited > worst[1]):
                worst = (ticket, waited)
            if len(rows) < LIST_LIMIT:
                rows.append(self._row(
                    self._ticket_label(ticket),
                    _("Waiting %(days)s days · %(stage)s · %(user)s", days=waited,
                      stage=ticket.stage_id.name or '', user=ticket.user_id.name or _("Unassigned")),
                    '', 'danger' if urgent else 'muted', 'helpdesk.ticket', ticket.id,
                    excerpt=self._excerpt(ticket.description)))
        oldest_wait = self._days_since(tickets[0].date or tickets[0].create_date, today) or 0
        brief['kpis'].append(self._kpi(
            'tickets', _("Open tickets"), str(len(tickets)),
            _("Oldest waiting %s days", oldest_wait),
            'danger' if worst else 'muted', 'helpdesk.ticket', domain=domain, name=_("Open tickets")))
        if worst:
            ticket, waited = worst
            self._risk(brief, 'high', _(
                "%(ticket)s has been waiting %(days)s days%(sla)s.",
                ticket=self._ticket_label(ticket), days=waited,
                sla=_(" and has missed its SLA") if ticket.sla_failed else ''),
                _("Resolve or give a firm update on %s first.", self._ticket_label(ticket)),
                'helpdesk.ticket', res_id=ticket.id)
        brief['sections'].append(self._section('tickets', _("Open tickets"), rows))
        return tickets.ids

    def _add_opportunities(self, partner, brief):
        """Open opportunities of the partner; returns their ids."""
        if 'crm.lead' not in self.env or not self._can_read('crm.lead'):
            return []
        domain = [('partner_id', 'child_of', partner.id), ('type', '=', 'opportunity'),
                  ('probability', '<', 100)]
        leads = self.env['crm.lead'].search(domain, order='expected_revenue desc')
        if not leads:
            return []
        brief['kpis'].append(self._kpi(
            'pipeline', _("Open pipeline"), self._money(sum(leads.mapped('expected_revenue'))),
            _("%s opportunities", len(leads)), 'muted', 'crm.lead', domain=domain,
            name=_("Opportunities")))
        brief['sections'].append(self._section('pipeline', _("Open opportunities"), [
            self._row(lead.name, _("%(stage)s · %(prob)s %%", stage=lead.stage_id.name or '',
                                   prob=round(lead.probability)),
                      self._money(lead.expected_revenue, lead.company_currency),
                      'muted', 'crm.lead', lead.id)
            for lead in leads[:LIST_LIMIT]]))
        return leads.ids

    def _add_tasks(self, project, today, brief):
        """Open tasks of the project with the late ones first; returns task ids."""
        Task = self.env['project.task']
        domain = [('project_id', '=', project.id)]
        if 'state' in Task._fields:
            domain.append(('state', 'not in', TASK_CLOSED_STATES))
        tasks = Task.search(domain, order='date_deadline asc, priority desc, id asc')
        if not tasks:
            return []
        now = fields.Datetime.now()
        late = tasks.filtered(lambda t: t.date_deadline and t.date_deadline < now)
        waiting = tasks.filtered(lambda t: getattr(t, 'state', '') == '04_waiting_normal')
        hint = _("%(late)s late, %(waiting)s waiting", late=len(late), waiting=len(waiting))
        brief['kpis'].append(self._kpi(
            'tasks', _("Open tasks"), str(len(tasks)), hint,
            'danger' if late else 'muted', 'project.task', domain=domain, name=_("Open tasks")))
        if late:
            oldest = (today - late[0].date_deadline.date()).days
            self._risk(brief, 'high' if oldest > 7 or len(late) > 3 else 'medium', _(
                "%(count)s tasks are past their deadline, the oldest by %(days)s days (%(task)s).",
                count=len(late), days=oldest, task=late[0].name),
                _("Go through the late tasks with their owners and reset realistic dates."),
                'project.task', domain=[('id', 'in', late.ids)], name=_("Late tasks"))
        if project.date and project.date < today:
            self._risk(brief, 'high', _(
                "The project end date (%(date)s) has passed with %(count)s tasks still open.",
                date=self._fmt_date(project.date), count=len(tasks)),
                _("Agree a new end date with the client and update the plan."),
                'project.project', res_id=project.id)
        rows = []
        for task in (late | tasks)[:LIST_LIMIT]:
            if task.date_deadline:
                days = (today - task.date_deadline.date()).days
                detail = _("Due %(date)s · %(days)s days late", date=self._fmt_date(task.date_deadline),
                           days=days) if days > 0 else _("Due %s", self._fmt_date(task.date_deadline))
            else:
                detail = _("No deadline")
            owners = ", ".join(task.user_ids.mapped('name')) if 'user_ids' in task._fields else ''
            rows.append(self._row(task.name, " · ".join(filter(None, [detail, owners])), '',
                                  'danger' if task in late else 'muted', 'project.task', task.id))
        brief['sections'].append(self._section(
            'tasks', _("Tasks needing attention"), rows,
            self._list_action('project.task', domain, _("Open tasks")) if len(tasks) > LIST_LIMIT else None))
        return tasks.ids

    def _add_messages(self, brief, today, domain, title):
        """Latest e-mails and chatter messages; returns the newest message date."""
        since = fields.Datetime.now() - timedelta(days=MESSAGE_DAYS)
        messages = self.env['mail.message'].search(expression.AND([domain, [
            ('message_type', 'in', ('email', 'comment')),
            ('date', '>=', since),
        ]]), order='date desc', limit=LIST_LIMIT)
        messages = messages.filtered(lambda m: m.model and m.res_id)
        if not messages:
            return None
        brief['sections'].append(self._section('messages', title, [
            self._row(msg.subject or msg.record_name or _("Message"),
                      _("%(date)s · %(author)s", date=self._fmt_date(msg.date),
                        author=msg.author_id.name or msg.email_from or ''),
                      '', 'muted', msg.model, msg.res_id, excerpt=self._excerpt(msg.body))
            for msg in messages]))
        return fields.Datetime.context_timestamp(self, messages[0].date).date()

    def _add_activities(self, targets, today, brief):
        """Pending activities on the given ``[(model, ids)]``; returns their count."""
        clauses = [[('res_model', '=', model), ('res_id', 'in', ids)]
                   for model, ids in targets if ids]
        if not clauses:
            return 0
        activities = self.env['mail.activity'].search(expression.OR(clauses),
                                                      order='date_deadline asc')
        if not activities:
            return 0
        overdue = activities.filtered(lambda a: a.date_deadline < today)
        brief['kpis'].append(self._kpi(
            'activities', _("Pending activities"), str(len(activities)),
            _("%s overdue", len(overdue)) if overdue else _("Next on %s",
                                                            self._fmt_date(activities[0].date_deadline)),
            'warning' if overdue else 'muted', 'mail.activity',
            domain=[('id', 'in', activities.ids)], name=_("Pending activities")))
        if overdue:
            first = overdue[0]
            self._risk(brief, 'medium', _(
                "%(count)s follow-ups are overdue, the oldest is \"%(name)s\" due %(date)s.",
                count=len(overdue), name=first.summary or first.activity_type_id.name or '',
                date=self._fmt_date(first.date_deadline)),
                _("Complete or reschedule the overdue follow-ups."),
                first.res_model, res_id=first.res_id)
        brief['sections'].append(self._section('activities', _("Pending activities"), [
            self._row(act.summary or act.activity_type_id.name or _("Activity"),
                      " · ".join(filter(None, [_("Due %s", self._fmt_date(act.date_deadline)),
                                               act.user_id.name, act.res_name])),
                      '', 'danger' if act in overdue else 'muted', act.res_model, act.res_id)
            for act in activities[:LIST_LIMIT]]))
        return len(activities)

    # -- narrative ------------------------------------------------------------

    def _narrative(self, brief, today):
        """Ask the LLM for the summary and next step; fall back to rules."""
        role = brief.pop('role', 'manager')
        fallback = self._rule_narrative(brief)
        client = LLMClient(self.env)
        if not client.is_configured():
            return fallback
        lang = self.env['res.lang']._lang_get(self.env.lang or 'en_US')
        facts = {
            'record': {'name': brief['title'], 'type': brief['subtitle'],
                       'today': self._fmt_date(today)},
            'key_figures': [{'label': k['label'], 'value': k['value'], 'detail': k['hint']}
                            for k in brief['kpis']],
            'risks': [r['text'] for r in brief['risks']],
            'details': [{'title': s['title'],
                         'items': [{k: v for k, v in row.items()
                                    if k in ('label', 'detail', 'amount', 'excerpt') and v}
                                   for row in s['rows']]}
                        for s in brief['sections']],
        }
        prompt = NARRATIVE_PROMPT.format(role=role,
                                         lang=lang.name if lang else 'English')
        try:
            raw = client.complete([
                {'role': 'system', 'content': prompt},
                {'role': 'user', 'content': json.dumps(facts, ensure_ascii=False)},
            ])
            data = self._parse_json(raw)
        except Exception as e:
            _logger.warning("[cyllo_ai] catch me up narrative failed: %s", e)
            fallback['notice'] = _("The AI summary could not be generated, so this "
                                   "briefing was built from rules.")
            return fallback
        if not data.get('summary'):
            return fallback
        mood = data.get('mood') if data.get('mood') in ('positive', 'neutral', 'negative') else 'unknown'
        return {
            'summary': str(data['summary']).strip(),
            'next_step': str(data.get('next_step') or fallback['next_step']).strip(),
            'mood': mood,
            'mood_reason': str(data.get('mood_reason') or '').strip(),
            'source': 'ai',
            'notice': '',
        }

    def _rule_narrative(self, brief):
        """Deterministic summary built from the ranked risks."""
        risks = brief['risks']
        if risks:
            summary = " ".join(r['text'] for r in risks[:3])
            next_step = risks[0]['next_step']
        else:
            summary = _("Nothing needs urgent attention: no overdue money, late work or "
                        "waiting tickets were found.")
            next_step = _("Use the conversation to ask about their upcoming needs.")
        return {'summary': summary, 'next_step': next_step, 'mood': 'unknown',
                'mood_reason': '', 'source': 'rules', 'notice': ''}

    @staticmethod
    def _parse_json(raw):
        """Parse the model's JSON reply, tolerating code fences or extra prose."""
        text = (raw or '').strip()
        text = re.sub(r'^```(?:json)?\s*|\s*```$', '', text)
        match = re.search(r'\{.*\}', text, re.S)
        data = json.loads(match.group(0) if match else text)
        if not isinstance(data, dict):
            raise ValueError("briefing reply is not a JSON object")
        return data

    # -- helpers --------------------------------------------------------------

    def _safe(self, func, *args):
        """Run a fact block, skipping it when the user may not read its data."""
        try:
            with self.env.cr.savepoint():
                return func(*args)
        except AccessError:
            _logger.debug("[cyllo_ai] catch me up skipped %s: no access", func.__name__)
            return None

    def _can_read(self, model):
        """True if the current user may read ``model``."""
        return self.env[model].check_access_rights('read', raise_exception=False)

    def _family(self, partner):
        """The commercial partner and all its contacts."""
        return self.env['res.partner'].with_context(active_test=False).search(
            [('id', 'child_of', partner.id)])

    def _to_company(self, amount, currency, company, day):
        """Convert ``amount`` into the current company's currency."""
        target = self.env.company.currency_id
        if not currency or currency == target:
            return amount
        return currency._convert(amount, target, company or self.env.company, day)

    def _money(self, amount, currency=None):
        """Format ``amount`` in ``currency`` (default: company currency)."""
        return format_amount(self.env, amount or 0.0, currency or self.env.company.currency_id)

    def _fmt_date(self, value):
        """Format a date or datetime in the user's language and timezone."""
        if not value:
            return ''
        if isinstance(value, datetime):
            value = fields.Datetime.context_timestamp(self, value).date()
        return format_date(self.env, value)

    def _days_since(self, value, today):
        """Whole days from ``value`` (date or datetime) to ``today``."""
        if not value:
            return None
        if isinstance(value, datetime):
            value = fields.Datetime.context_timestamp(self, value).date()
        return (today - value).days

    @staticmethod
    def _excerpt(html):
        """Plain-text excerpt of an HTML body."""
        text = re.sub(r'\s+', ' ', html2plaintext(html or '')).strip()
        return text[:EXCERPT_CHARS] + ('…' if len(text) > EXCERPT_CHARS else '')

    @staticmethod
    def _ticket_label(ticket):
        """Human reference of a ticket, e.g. ``Ticket TCK0012 (Damaged delivery)``."""
        return _("Ticket %(ref)s (%(name)s)", ref=ticket.ticket or '#%s' % ticket.id,
                 name=ticket.name or '')

    @staticmethod
    def _list_action(res_model, domain, name):
        """Link payload that opens a filtered list of records."""
        return {'res_model': res_model, 'domain': domain, 'name': name}

    def _kpi(self, key, label, value, hint, tone, res_model, res_id=None, domain=None, name=None):
        """One key-figure card with the record or list it links to."""
        return {'key': key, 'label': label, 'value': value, 'hint': hint or '', 'tone': tone,
                'link': {'res_model': res_model, 'res_id': res_id} if res_id
                else self._list_action(res_model, domain or [], name or label)}

    def _risk(self, brief, severity, text, next_step, res_model, res_id=None, domain=None, name=None):
        """Record a risk with its suggested next step and its source link."""
        brief['risks'].append({
            'severity': severity, 'text': text, 'next_step': next_step,
            'link': {'res_model': res_model, 'res_id': res_id} if res_id
            else self._list_action(res_model, domain or [], name or text),
        })

    @staticmethod
    def _section(key, title, rows, more=None):
        """A titled list of linked rows."""
        return {'key': key, 'title': title, 'rows': rows, 'more': more}

    @staticmethod
    def _row(label, detail, amount, tone, res_model, res_id, excerpt=''):
        """One linked row of a section."""
        return {'label': label, 'detail': detail, 'amount': amount, 'tone': tone,
                'excerpt': excerpt, 'link': {'res_model': res_model, 'res_id': res_id}}
