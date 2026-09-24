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
from odoo import models, fields, api, _
import logging
import ast
import json

_logger = logging.getLogger(__name__)


class DashboardAlertCondition(models.Model):
    """One condition row: which measure to watch, operator, and threshold."""
    _name = 'dashboard.alert.condition'
    _description = 'Dashboard Alert Condition'
    _order = 'sequence, id'

    alert_id = fields.Many2one('dashboard.alert', string='Alert', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)

    measure_alias = fields.Char(string='Measure Field (alias)', required=True,
                                help='SQL alias of the measure column in the query result')
    measure_label = fields.Char(string='Measure Label',
                                help='Human-readable label shown in the UI and notifications')

    condition = fields.Selection([
        ('gt', 'Greater Than'),
        ('lt', 'Less Than'),
        ('eq', 'Equals'),
        ('ge', 'Greater or Equal'),
        ('le', 'Less or Equal'),
    ], string='Condition', required=True, default='gt')

    value = fields.Float(string='Threshold Value', required=True)
    is_met = fields.Boolean(
        string='Condition Met Previously',
        default=False,
        help='Prevents repeat notifications until the condition resets below threshold.'
    )


class DashboardAlert(models.Model):
    _name = 'dashboard.alert'
    _description = 'Dashboard Alert'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Alert Name', required=True)
    sheet_id = fields.Many2one('dashboard.sheet', string='Target Widget', required=True, ondelete='cascade')

    # ── Legacy single-condition fields (kept for backward compatibility) ──
    condition = fields.Selection([
        ('gt', 'Greater Than'),
        ('lt', 'Less Than'),
        ('eq', 'Equals'),
        ('ge', 'Greater or Equal'),
        ('le', 'Less or Equal'),
    ], string='Condition (legacy)', default='gt')
    value = fields.Float(string='Threshold Value (legacy)')

    # ── Multi-measure conditions ──
    condition_ids = fields.One2many(
        'dashboard.alert.condition', 'alert_id',
        string='Measure Conditions',
        help='Alert triggers when ANY of these conditions is met.'
    )

    # ── Dimension-level filter ──
    dimension_filter = fields.Boolean(
        string='Filter by Dimension Value',
        default=False,
        help='If enabled, only rows where the selected dimension equals the specified value are checked.'
    )
    dimension_alias = fields.Char(
        string='Dimension Field (alias)',
        help='SQL alias of the X-axis dimension column'
    )
    dimension_label = fields.Char(string='Dimension Label')
    dimension_value = fields.Char(
        string='Dimension Value to Watch',
        help='E.g. "Customer A" — only rows matching this dimension value are evaluated.'
    )

    user_id = fields.Many2one('res.users', string='Person to Notify',
                              default=lambda self: self.env.user, required=True)
    notify_user_ids = fields.Many2many('res.users', 'dashboard_alert_res_users_rel',
                                       'alert_id', 'user_id', string='Additional Recipients')

    trigger_model_id = fields.Many2one('ir.model', string='Trigger Model')
    last_run = fields.Datetime(string='Last Checked')
    is_condition_met = fields.Boolean(string='Condition Met Previously', default=False)
    send_email = fields.Boolean(string='Send Email', default=False)
    screen_notification = fields.Boolean(string='Show Screen Warning', default=True)


    automation_ids = fields.Many2many('base.automation', string='Automated Actions')

    _sql_constraints = [
        ('sheet_user_unique', 'unique(sheet_id, user_id)', 'An alert for this chart already exists!')
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('trigger_model_id') and vals.get('sheet_id'):
                sheet = self.env['dashboard.sheet'].browse(vals['sheet_id'])
                if sheet and sheet.table_ids:
                    main_table = sheet.table_ids.filtered(lambda x: not x.linked)
                    vals['trigger_model_id'] = main_table[0].model_id.id if main_table else sheet.table_ids[0].model_id.id
                elif sheet and sheet.query:
                    query_low = sheet.query.lower()
                    if any(x in query_low for x in ['sale_order', 'sale_order_line', 'sale_report']):
                        vals['trigger_model_id'] = self.env['ir.model']._get('sale.order').id
                    elif any(x in query_low for x in ['account_move', 'account_move_line', 'account_invoice']):
                        vals['trigger_model_id'] = self.env['ir.model']._get('account.move').id
                    elif any(x in query_low for x in ['purchase_order', 'purchase_order_line', 'purchase_report']):
                        vals['trigger_model_id'] = self.env['ir.model']._get('purchase.order').id
                    elif any(x in query_low for x in ['product_product', 'product_template']):
                        vals['trigger_model_id'] = self.env['ir.model']._get('product.product').id
                    elif 'stock_picking' in query_low:
                        vals['trigger_model_id'] = self.env['ir.model']._get('stock.picking').id

        records = super().create(vals_list)
        for record in records:
            record._update_automation()
        return records

    def write(self, vals):
        if self.env.context.get('skip_alert_sync'):
            return super().write(vals)

        if any(k in vals for k in ['value', 'condition', 'condition_ids',
                                   'dimension_filter', 'dimension_alias', 'dimension_value']):
            vals['is_condition_met'] = False

        res = super().write(vals)
        if any(k in vals for k in ['trigger_model_id', 'value', 'condition',
                                   'sheet_id', 'condition_ids']):
            for record in self:
                record._update_automation()
        return res

    def _update_automation(self):
        """Dual Automation setup: Watches both changes and deletions for ALL models in the query traversal."""
        self.ensure_one()
        self.automation_ids.sudo().unlink()

        if self.sheet_id:
            measures = self.sheet_id.axis_ids.filtered(lambda x: x.type == 'measure')
            models_to_watch = self.env['ir.model']

            # 1. Preset model support
            for sheet_axis in self.sheet_id.axis_ids.filtered(lambda a: a.preset_id):
                preset = sheet_axis.preset_id
                if preset.model_id:
                    models_to_watch = models_to_watch | preset.model_id
                if sheet_axis.variable_configs:
                    try:
                        configs = json.loads(sheet_axis.variable_configs)
                        for cfg in configs:
                            col = cfg.get('original_column') or cfg.get('column') or ""
                            if '.' in col:
                                field_name = col.split('.')[-1].replace('(', '').replace(')', '')
                                f_rec = self.env['ir.model.fields'].sudo().search([
                                    ('name', '=', field_name),
                                    ('model', 'in', self.sheet_id.table_ids.mapped('model'))
                                ], limit=1)
                                if f_rec:
                                    models_to_watch = models_to_watch | f_rec.model_id
                    except Exception:
                        pass

            # 2. Measure field model support
            for msr in measures:
                col = msr.column
                if not col:
                    continue
                field_name = col.split('.')[-1].replace('(', '').replace(')', '')
                field_recs = self.env['ir.model.fields'].sudo().search([
                    ('model', 'in', self.sheet_id.table_ids.mapped('model')),
                    ('name', '=', field_name)
                ])
                for f_rec in field_recs:
                    table = self.sheet_id.table_ids.filtered(lambda x: x.model == f_rec.model)
                    if table:
                        models_to_watch = models_to_watch | table.model_id

            if not models_to_watch:
                models_to_watch = self.sheet_id.table_ids.filtered(lambda x: not x.linked).mapped('model_id')
            if not models_to_watch:
                return

            new_automations = []
            code = f"env['dashboard.alert'].browse({self.id})._evaluate_alert()"

            for model in models_to_watch:
                action_name_save = f"Watchdog (Create/Write): {self.name} [{model.model}]"
                action_save = self.env['ir.actions.server'].sudo().create({
                    'name': action_name_save, 'model_id': model.id,
                    'state': 'code', 'code': code,
                })
                auto_save = self.env['base.automation'].sudo().create({
                    'name': action_name_save, 'model_id': model.id,
                    'trigger': 'on_create_or_write', 'action_server_ids': [(6, 0, [action_save.id])],
                })
                new_automations.append(auto_save.id)

            self.with_context(skip_alert_sync=True).write({'automation_ids': [(6, 0, new_automations)]})

    @api.model
    def _evaluate_all_alerts(self):
        """Cron triggered method to evaluate all active alerts."""
        alerts = self.search([])
        alerts._evaluate_alert()

    def _evaluate_alert(self):
        """Evaluate alert: supports multi-measure conditions and optional dimension-level filtering."""
        self = self.sudo().exists()
        if not self:
            return
        for alert in self:
            try:
                query = alert.sheet_id.query
                if not query:
                    continue

                self.env.flush_all()
                self.env.cr.execute(query)
                res = self.env.cr.dictfetchall()

                if not res:
                    alert.is_condition_met = False
                    continue

                # ── Optional: narrow rows to a specific dimension value ──
                if alert.dimension_filter and alert.dimension_alias and alert.dimension_value:
                    dim_alias = alert.dimension_alias
                    dim_val = alert.dimension_value
                    res = [
                        row for row in res
                        if str(row.get(dim_alias, '')).strip() == str(dim_val).strip()
                    ]

                # ── Build effective conditions list ──
                # Use new condition_ids if populated; fall back to legacy single condition.
                effective_conditions = []
                if alert.condition_ids:
                    for cond in alert.condition_ids:
                        effective_conditions.append({
                            'alias': cond.measure_alias,
                            'label': cond.measure_label or cond.measure_alias,
                            'op': cond.condition,
                            'threshold': cond.value,
                        })
                elif alert.condition and alert.value is not None:
                    # Legacy fallback: use the first numeric measure
                    measure_keys = []
                    try:
                        measure_keys = ast.literal_eval(alert.sheet_id.measure) if alert.sheet_id.measure else []
                    except Exception:
                        pass
                    if not measure_keys and res:
                        measure_keys = [k for k, v in res[0].items() if isinstance(v, (int, float))]
                    alias = measure_keys[0] if measure_keys else None
                    effective_conditions.append({
                        'alias': alias,
                        'label': alias or 'measure',
                        'op': alert.condition,
                        'threshold': alert.value,
                    })

                if not effective_conditions:
                    continue

                def _check(op, val, threshold):
                    if op == 'gt': return val > threshold
                    if op == 'ge': return val >= threshold
                    if op == 'lt': return val < threshold
                    if op == 'le': return val <= threshold
                    if op == 'eq': return val == threshold
                    return False

                # ── Evaluate each condition independently ──
                # Each condition tracks its own is_met flag.
                # However, we collect ALL new notifications for this run into ONE fused message.
                triggered_summaries = []
                
                if alert.condition_ids:
                    for cond_rec in alert.condition_ids:
                        alias     = cond_rec.measure_alias
                        threshold = cond_rec.value
                        op        = cond_rec.condition
                        hit_value = None

                        for row in res:
                            current_value = row.get(alias)
                            if current_value is None:
                                current_value = next(
                                    (v for v in row.values() if isinstance(v, (int, float))), None
                                )
                            if current_value is not None and _check(op, current_value, threshold):
                                hit_value = current_value
                                break

                        if hit_value is not None:          # condition is currently breached
                            if not cond_rec.is_met:        # only include if not already notified
                                triggered_summaries.append(f"{cond_rec.measure_label or alias}: {hit_value}")
                                cond_rec.with_context(skip_alert_sync=True).write({'is_met': True})
                        else:
                            if cond_rec.is_met:
                                cond_rec.with_context(skip_alert_sync=True).write({'is_met': False})

                else:
                    # ── Legacy fallback ──
                    triggered = False
                    trigger_info = []
                    for cond in effective_conditions:
                        alias, threshold, op = cond['alias'], cond['threshold'], cond['op']
                        for row in res:
                            val = row.get(alias)
                            if val is not None and _check(op, val, threshold):
                                triggered = True
                                trigger_info.append(f"{cond['label']}: {val}")
                                break
                    if triggered and not alert.is_condition_met:
                        triggered_summaries = trigger_info
                        alert.is_condition_met = True
                    elif not triggered:
                        alert.is_condition_met = False

                if triggered_summaries:
                    try:
                        alert._send_notification("; ".join(triggered_summaries))
                    except Exception as e:
                        _logger.error(f"Notification Error: {str(e)}")

                # Real-time graph refresh signal
                try:
                    dashboard_config = alert.env['dashboard.config'].search(
                        [('sheet_ids', 'in', alert.sheet_id.ids)], limit=1)
                    alert.env['bus.bus']._sendone(alert.user_id.partner_id, 'notification', {
                        'type': 'refresh_graph',
                        'dashboard_id': dashboard_config.id if dashboard_config else 0,
                        'sheet_id': alert.sheet_id.id,
                        'clear_cache': True,
                    })
                except Exception:
                    pass

                super(DashboardAlert, alert).write({'last_run': fields.Datetime.now()})
            except Exception as e:
                _logger.error(f"Watchdog Error: {str(e)}")

    def _send_notification(self, trigger_summary):
        """Send inbox + optional email notification."""
        self.ensure_one()
        subject = _("Dashboard Alert: %s") % self.name
        dashboard_config = self.env['dashboard.config'].search(
            [('sheet_ids', 'in', self.sheet_id.ids)], limit=1)
        action_id = self.env.ref('cyllo_analytics.cyllo_dashboard_action').id
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')

        dashboard_uri = (
            f"/web#action={action_id}&id={dashboard_config.id}&sheet_id={self.sheet_id.id}"
            if dashboard_config else "#"
        )
        full_url = f"{base_url}{dashboard_uri}"

        plain_body = _("Alert '%s' triggered: %s") % (self.name, trigger_summary)
        link_body = (
            f'<a href="{full_url}" style="font-weight:bold; text-decoration:none; color:#71639e;">'
            f'{plain_body}</a>'
        )

        odoobot_id = self.env.ref('base.partner_root').id

        # ── Recipients ──
        recipients = self.user_id | self.notify_user_ids
        recipient_partners = recipients.mapped('partner_id')

        # ── 1. Create Odoo Inbox Message ──
        msg = self.env['mail.message'].sudo().create({
            'author_id': odoobot_id,
            'model': 'dashboard.config',
            'res_id': dashboard_config.id if dashboard_config else 0,
            'body': link_body,
            'subject': subject,
            'message_type': 'comment',
            'subtype_id': self.env.ref('mail.mt_comment').id,
            'partner_ids': [(6, 0, recipient_partners.ids)],
        })

        # ── 2. Create Notifications & Bus signals for each recipient ──
        for partner in recipient_partners:
            self.env['mail.notification'].sudo().create({
                'mail_message_id': msg.id,
                'res_partner_id': partner.id,
                'notification_type': 'inbox',
            })
            self.env['bus.bus']._sendone(partner, 'mail.message/inbox', {
                'id': msg.id, 'body': link_body, 'subject': subject,
                'model': 'dashboard.config',
                'res_id': dashboard_config.id if dashboard_config else 0,
            })

            # Real-time Screen Warning
            if self.screen_notification:
                payload = {
                    'id': dashboard_config.id if dashboard_config else 0,
                    'sheet_id': self.sheet_id.id,
                    'title': subject,
                    'message': plain_body,
                    'type': 'warning',
                    'sticky': True,
                }
                self.env['bus.bus']._sendone(partner, 'cyllo_analytics_alert', payload)

            # Refresh Graph Signal
            self.env['bus.bus']._sendone(partner, 'notification', {
                'type': 'refresh_graph',
                'dashboard_id': dashboard_config.id if dashboard_config else 0,
                'sheet_id': self.sheet_id.id,
                'clear_cache': True,
            })

        # ── 3. Send Emails ──
        if self.send_email:
            # Aggregate all emails into one mail record or send individually to ensure deliverability
            # To avoid Nathan getting it twice, we ensure unique recordset
            unique_recipients = recipients.sudo()
            for user in unique_recipients:
                if not user.email:
                    _logger.warning(f"Cyllo Alert: Skipping user {user.name} - no email configured.")
                    continue
                
                self.env['mail.mail'].sudo().create({
                    'subject': subject,
                    'body_html': f"<div>{plain_body}</div><br/><small>Ref: {self.name}</small>",
                    'email_to': user.email,
                    'recipient_ids': [(4, user.partner_id.id)],
                    'auto_delete': True,
                }).send()

    def unlink(self):
        self.mapped('automation_ids').sudo().unlink()
        return super().unlink()
