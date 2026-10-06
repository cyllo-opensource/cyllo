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
import logging
from ast import literal_eval

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


def level_sort_key(line):
    """Sort key working for saved records and for unsaved form lines."""
    return (line.sequence, line.id if isinstance(line.id, int) else 0)


class ApprovalRule(models.Model):
    _name = 'approval.rule'
    _description = 'Approval Rule'

    name = fields.Char(
        required=True,
        help="Display name for this approval rule."
    )
    model_id = fields.Many2one(
        'ir.model',
        string='Target Model',
        help="The Odoo model this rule applies to."
    )
    model_name = fields.Char(
        related='model_id.model',
        store=True,
        help="Technical name of the target model."
    )
    request_ids = fields.One2many(
        'approval.request',
        'rule_id',
        help="History of approval requests triggered by this rule."
    )
    approval_line_ids = fields.One2many(
        'approval.rule.line',
        'rule_id',
        string='Approval Levels',
        copy=True,
        help="The successive approval levels of this rule. Each level is "
             "requested only once the previous one has been approved."
    )
    level_count = fields.Integer(
        string='Levels',
        compute='_compute_level_info',
        store=True,
        help="Number of approval levels configured on this rule."
    )
    approver_names = fields.Char(
        string='Approvers',
        compute='_compute_level_info',
        store=True,
        help="Approvers of every level, in the order they are requested."
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        help="The company this approval rule belongs to."
    )
    rule_type = fields.Selection([
        ('button', 'Button'),
        ('state', 'State Change'),
        ('server', 'Server Action'),
    ], required=True, default='button',
        help="Specify what triggers the approval: "
             "clicking a button, changing a state/stage, or a server action.")

    state_field_id = fields.Many2one(
        'ir.model.fields',
        string='State Field',
        domain="[('model_id', '=', model_id), '|', ('name', 'in', ['state', 'stage_id', 'status']), ('ttype', '=', 'selection')]",
        help="The field that represents the state or stage in the target model."
    )
    state_field_name = fields.Char(related='state_field_id.name', store=True)
    state_field_type = fields.Selection(
        related='state_field_id.ttype',
        string='Field Type'
    )
    state_field_relation = fields.Char(
        related='state_field_id.relation',
        string='Related Model',
        help='For many2one fields, this is the comodel'
    )
    state_to_selection_id = fields.Many2one(
        'ir.model.fields.selection',
        string="Target State (Selection)",
        domain="[('field_id', '=', state_field_id)]",
        help="The specific selection value that requires approval when selected."
    )
    state_values_m2o_ids = fields.Many2many(
        'approval.state.value',
        string='Available State Values',
        compute='_compute_state_values_m2o',
        store=False
    )
    state_to_m2o_value_id = fields.Many2one(
        'approval.state.value',
        string="Target State (Stage)",
        domain="[('id', 'in', state_values_m2o_ids)]",
        help="The specific stage that requires approval when entered."
    )
    user_id = fields.Many2one(
        'res.users', string='Approver',
        help="Approver of the first level. Kept in sync with the first line "
             "of the Approval Levels tab."
    )
    group_id = fields.Many2one(
        'res.groups', string='Approver Group',
        help="Approver group of the first level. Kept in sync with the first "
             "line of the Approval Levels tab."
    )
    button_id = fields.Many2one('ir.buttons',
                                domain="[('model_id','=',model_id)]",
                                help="Select the button that requires an approval.")

    server_action_id = fields.Many2one(
        'ir.actions.server',
        domain="[('model_id','=',model_id)]",
        help="The server action that requires approval before execution."
    )

    sequence = fields.Integer(
        default=1,
        help="The order in which rules are processed if multiple rules apply."
    )
    auto_execute = fields.Boolean(
        'Execute on Final Approval',
        default=True,
        help="Once the last approval level is approved, run the original "
             "action automatically (click the button / apply the state) "
             "instead of asking the requester to trigger it again."
    )
    domain = fields.Char(
        default='[]',
        help="A Python domain to further filter which records this rule applies to."
    )
    is_comment = fields.Boolean(
        'Allow Comment',
        help="If checked, the requester can add a comment to the request."
    )
    is_email = fields.Boolean('Notify Email',
                              help="Enable email notifications for this rule.")
    is_email_request = fields.Boolean(
        'Notify on Request',
        help="Send an email to the approver when a request is created."
    )
    is_email_approve = fields.Boolean(
        'Notify on Approval',
        help="Send an email to the requester when the request is approved."
    )
    is_email_reject = fields.Boolean(
        'Notify on Rejection',
        help="Send an email to the requester when the request is rejected."
    )

    @api.constrains('model_id')
    def _constraint_model_id(self):
        if not self.model_id:
            raise ValidationError('Please choose a Model.')

    @api.constrains('approval_line_ids')
    def _constraint_approval_line_ids(self):
        for rule in self:
            if not rule.approval_line_ids:
                raise ValidationError(_(
                    "Rule '%s' needs at least one approval level."
                ) % rule.name)

    @api.depends('approval_line_ids.sequence', 'approval_line_ids.user_id',
                 'approval_line_ids.group_id')
    def _compute_level_info(self):
        """Summarize the configured levels for the list/search views."""
        for rule in self:
            levels = rule._get_levels()
            rule.level_count = len(levels)
            rule.approver_names = ' → '.join(
                level.approver_name for level in levels) or False

    @api.depends('state_field_id', 'state_field_relation')
    def _compute_state_values_m2o(self):
        """Dynamically fetch all records from the related model."""
        for rec in self:
            rec.state_values_m2o_ids = False

            if not rec.state_field_relation:
                continue

            try:
                comodel = self.env[rec.state_field_relation]
                records = comodel.search([])

                StateValue = self.env['approval.state.value']
                value_ids = []

                for record in records:
                    display_name = record.display_name or record.name
                    value = StateValue.search([
                        ('res_model', '=', rec.state_field_relation),
                        ('res_id', '=', record.id),
                    ], limit=1)

                    if not value:
                        value = StateValue.create({
                            'res_model': rec.state_field_relation,
                            'res_id': record.id,
                            'name': display_name,
                        })
                    else:
                        value.write({'name': display_name})
                    value_ids.append(value.id)
                rec.state_values_m2o_ids = value_ids

            except Exception as e:
                _logger.warning(
                    f"Failed to load state values for {rec.state_field_relation}: {e}")
                rec.state_values_m2o_ids = False

    @api.onchange('state_field_id')
    def _onchange_state_field_id(self):
        """Clear state values when changing the state field."""
        self.state_to_selection_id = False
        self.state_to_m2o_value_id = False

    @api.onchange('is_email')
    def _onchange_is_email(self):
        """Reset email notification options when email support is disabled."""
        if not self.is_email:
            self.is_email_request = False
            self.is_email_approve = False
            self.is_email_reject = False

    @api.model_create_multi
    def create(self, vals_list):
        """Patch the target model's method when a rule is created."""
        for vals in vals_list:
            if not vals.get('approval_line_ids') and (
                    vals.get('user_id') or vals.get('group_id')):
                # A rule defined the legacy way (single approver on the rule)
                # becomes a rule with one approval level.
                vals['approval_line_ids'] = [fields.Command.create({
                    'sequence': 10,
                    'user_id': vals.get('user_id'),
                    'group_id': vals.get('group_id'),
                })]
        records = super().create(vals_list)
        for rec in records:
            rec._sync_legacy_approver()
            rec._patch_method()
            rec._create_dynamic_fields()
        return records

    def write(self, vals):
        res = super().write(vals)
        if 'approval_line_ids' in vals:
            for rec in self:
                rec._sync_legacy_approver()
        if any(key in vals for key in
               ['model_id', 'rule_type', 'button_id', 'state_field_id']):
            for rec in self:
                rec._patch_method()
                rec._create_dynamic_fields()
        return res

    def _sync_legacy_approver(self):
        """Mirror the first level on the rule for search/grouping purposes."""
        for rule in self:
            first = rule._get_levels()[:1]
            values = {
                'user_id': first.user_id.id,
                'group_id': first.group_id.id,
            }
            if (rule.user_id.id, rule.group_id.id) != (
                    values['user_id'], values['group_id']):
                super(ApprovalRule, rule).write(values)

    # ------------------------------------------------------------------
    # Approval levels
    # ------------------------------------------------------------------
    def _get_levels(self):
        """Return the approval levels of this rule, lowest sequence first."""
        self.ensure_one()
        return self.approval_line_ids.sorted(level_sort_key)

    def _get_next_level(self, line):
        """Return the level coming right after ``line``, if any."""
        self.ensure_one()
        levels = self._get_levels()
        if not line:
            return levels[:1]
        for index, level in enumerate(levels):
            if level == line:
                return levels[index + 1:index + 2]
        return levels.browse()

    def _get_cycle_requests(self, res_model, res_id):
        """Return the requests of the running approval cycle for a record.

        A rejection closes the cycle: everything created afterwards belongs to
        a new attempt and the levels have to be approved again.
        """
        self.ensure_one()
        requests = self.env['approval.request'].sudo().search([
            ('rule_id', '=', self.id),
            ('res_model', '=', res_model),
            ('res_id', '=', res_id),
        ], order='id asc')
        rejected = requests.filtered(lambda req: req.state == 'rejected')
        if rejected:
            last_rejected = max(rejected.ids)
            requests = requests.filtered(lambda req: req.id > last_rejected)
        return requests

    def _get_pending_level(self, res_model, res_id):
        """Return the first level of the cycle that is not approved yet."""
        self.ensure_one()
        levels = self._get_levels()
        if not levels:
            return self.env['approval.rule.line']
        approved = self._get_cycle_requests(res_model, res_id).filtered(
            lambda req: req.state == 'approved')
        approved_levels = approved.line_id
        if levels and any(not req.line_id for req in approved):
            # Requests created before this rule had levels approved level one.
            approved_levels |= levels[0]
        for level in levels:
            if level not in approved_levels:
                return level
        return self.env['approval.rule.line']

    def _is_user_approver(self, user):
        """Whether ``user`` approves at least one level of this rule."""
        self.ensure_one()
        for level in self._get_levels():
            if level.user_id == user or (
                    level.group_id and level.group_id in user.groups_id):
                return True
        return False

    def _get_approver_group_ids(self, user):
        """Approver groups of this rule the given user is a member of."""
        self.ensure_one()
        return {
            level.group_id.id for level in self._get_levels()
            if level.group_id and level.group_id in user.groups_id
        }

    def _match_record(self, record):
        """Whether the rule domain selects this record."""
        self.ensure_one()
        try:
            domain = literal_eval(self.domain or '[]')
        except (ValueError, SyntaxError):
            _logger.warning("Invalid domain on approval rule %s: %s",
                            self.name, self.domain)
            domain = []
        if not domain:
            return True
        return bool(record.sudo().filtered_domain(domain))

    def _approval_wizard_action(self, record, level):
        """Action opening the confirmation wizard for the given level."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Approval Required'),
            'res_model': 'approval.request.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_rule_id': self.id,
                'default_line_id': level.id,
                'default_res_model': record._name,
                'default_res_id': record.id,
            },
        }

    def _check_record_approval(self, record):
        """Return the wizard action when ``record`` still needs an approval.

        Returns ``None`` once every level of the rule has been approved, so
        that the caller can proceed with the original action.
        """
        self.ensure_one()
        pending = self._get_cycle_requests(record._name, record.id).filtered(
            lambda req: req.state == 'pending')
        if pending:
            request = pending[0]
            raise ValidationError(_(
                "Approval '%(rule)s' is already pending at %(level)s "
                "(approver: %(approver)s)."
            ) % {
                'rule': self.name,
                'level': request.level_name or _('level 1'),
                'approver': request.approver_name or _('n/a'),
            })
        level = self._get_pending_level(record._name, record.id)
        if not level:
            return None
        return self._approval_wizard_action(record, level)

    def _execute_after_approval(self, record, request):
        """Run the approved action once the last level said yes.

        The original action is replayed on behalf of the requester with the
        rule neutralised, so that the requester does not have to trigger it a
        second time. A failure is reported in the chatter instead of undoing
        the approval itself.
        """
        self.ensure_one()
        if not self.auto_execute:
            return None
        bypass = list(self.env.context.get('approval_bypass_rule_ids') or [])
        bypass.append(self.id)
        user = request.requested_by or self.env.user
        target = record.with_user(user).with_context(
            approval_bypass_rule_ids=bypass)
        try:
            with self.env.cr.savepoint():
                return self._run_approved_action(target, bypass)
        except Exception as error:  # noqa: BLE001 - reported, never swallowed
            _logger.warning(
                "Approval rule %s could not replay its action on %s(%s): %s",
                self.name, record._name, record.id, error)
            message = _(
                "The approval is complete but '%(rule)s' could not be applied "
                "automatically: %(error)s"
            ) % {'rule': self.name, 'error': error}
            if hasattr(record, '_message_log'):
                record.sudo()._message_log(body=message)
            request.sudo()._message_log(body=message)
            return None

    def _run_approved_action(self, target, bypass):
        """Replay the very action the approval was requested for."""
        self.ensure_one()
        if self.rule_type == 'button' and self.button_id:
            return getattr(target, self.button_id.name)()
        if self.rule_type == 'state' and self.state_field_name:
            value = self._get_target_state_value()
            if value is not None:
                return target.write({self.state_field_name: value})
            return None
        if self.rule_type == 'server' and self.server_action_id:
            return self.server_action_id.with_user(target.env.user).with_context(
                active_model=target._name,
                active_id=target.id,
                active_ids=target.ids,
                approval_bypass_rule_ids=bypass,
            ).run()
        return None

    def _create_dynamic_fields(self):
        """Create required fields on target model if missing."""
        IrModelFields = self.env['ir.model.fields']
        model_fields = self.env[self.model_id.model]._fields
        fields_to_create = [
            {
                'name': 'x_approval_request_ids',
                'field_description': 'Approval Requests',
                'ttype': 'many2many',
                'relation': 'approval.request',
                'copied': False,
            },
            {
                'name': 'x_is_state_approval',
                'field_description': 'Is State Approval',
                'ttype': 'boolean',
                'copied': False,
            },
            {
                'name': 'x_approval_comment',
                'field_description': 'Approval Comment',
                'ttype': 'text',
                'copied': False,
            },
            {
                'name': 'x_current_approver_id',
                'field_description': 'Current Approver',
                'ttype': 'many2one',
                'relation': 'res.users',
                'copied': False,

            },
            {
                'name': 'x_current_group_id',
                'field_description': 'Current Approver Group',
                'ttype': 'many2one',
                'relation': 'res.groups',
                'copied': False,
            },
            {
                'name': 'x_approval_level_info',
                'field_description': 'Approval Level',
                'ttype': 'char',
                'copied': False,
            },
            {
                'name': 'x_approval_request_count',
                'field_description': 'Approval Requests',
                'ttype': 'integer',
                'copied': False,
            },
        ]
        created = False
        for field_data in fields_to_create:
            if field_data['name'] not in model_fields:
                IrModelFields.sudo().create({
                    **field_data,
                    'model_id': self.model_id.id,
                })
                created = True

        if created:
            # invalidate_model() flushes first: dropping the cache without
            # flushing would lose the pending writes of the running load.
            self.env['ir.ui.view'].invalidate_model()

    @api.model
    def _register_hook(self):
        """Re-apply patches for all existing rules at module load."""
        res = super()._register_hook()
        rules = self.sudo().search([])
        for rule in rules:
            try:
                rule._backfill_levels()
                rule._patch_method()
            except Exception as e:
                _logger.warning("Failed to patch rule %s: %s", rule.name, e)
        return res

    def _backfill_levels(self):
        """Give a level to rules configured before levels existed."""
        self.ensure_one()
        if self.approval_line_ids or not (self.user_id or self.group_id):
            return
        self.env['approval.rule.line'].sudo().create({
            'rule_id': self.id,
            'sequence': 10,
            'user_id': self.user_id.id,
            'group_id': self.group_id.id,
        })

    def _patch_method(self):
        """Patch the target model method based on the configured rule type."""
        model = self.env[self.model_name]
        if self.rule_type == 'state':
            return self._patch_state_change(model)
        elif self.rule_type == 'button':
            return self._patch_button_method(model)

    def _get_target_state_value(self):
        """Get the target state value regardless of field type."""
        self.ensure_one()
        if self.state_field_type == 'selection':
            return self.state_to_selection_id.value
        elif self.state_field_type == 'many2one':
            return self.state_to_m2o_value_id.res_id if self.state_to_m2o_value_id else None
        return None

    @api.model
    def _get_ordered_rules(self, model_name, trigger_type,
                           state_field_name=None, trigger_value=None):
        """Get rules matching the trigger, ordered by sequence."""
        domain = [
            ('model_name', '=', model_name),
            ('rule_type', '=', trigger_type),
            '|', ('company_id', '=', False), ('company_id', 'in', self.env.companies.ids)
        ]
        if trigger_type == 'button':
            # Matched on the method name, not on the ir.buttons id: the button
            # records are re-synced from the views and their ids do not
            # survive, while the method a rule guards always does.
            domain.append(('button_id.name', '=', trigger_value))
        else:  # state change
            domain.append(('state_field_name', '=', state_field_name))
            state_domain = [('state_to_selection_id.value', '=', trigger_value)]
            if isinstance(trigger_value, int) or (
                    isinstance(trigger_value, str) and trigger_value.isdigit()):
                state_domain = ['|'] + state_domain + [
                    ('state_to_m2o_value_id.res_id', '=', int(trigger_value))]

            domain += state_domain
        rules = self.search(domain).sorted(lambda r: r.sequence)
        bypass = self.env.context.get('approval_bypass_rule_ids') or []
        return rules.filtered(lambda rule: rule.id not in bypass)

    def _patch_button_method(self, model):
        """Patch a button method to enforce approval workflow rules."""
        button = self.button_id
        if button:
            method_name = button.name
            if not hasattr(model, method_name):
                raise ValidationError(
                    f"Method '{method_name}' not found on model '{self.model_name}'.")

            original_method = getattr(model.__class__, method_name)
            if getattr(original_method, '_approval_interceptor', False):
                # Already patched. Testing the method itself rather than a
                # flag on the class matters: creating the dynamic fields
                # rebuilds the registry classes and drops the patch, and a
                # stale flag would then keep it from ever coming back.
                return

            def intercepted_method(record, *args, **kwargs):
                Rule = record.env['approval.rule'].sudo()
                rules = Rule._get_ordered_rules(
                    model_name=record._name,
                    trigger_type='button',
                    trigger_value=method_name
                )
                for rule in rules:
                    for rec in record:
                        if not rule._match_record(rec):
                            continue
                        action = rule._check_record_approval(rec)
                        if action:
                            return action
                return original_method(record, *args, **kwargs)
            intercepted_method._approval_interceptor = True
            setattr(model.__class__, method_name, intercepted_method)

    def _patch_state_change(self, model):
        original_write = model.__class__.write
        if getattr(original_write, '_approval_interceptor', False):
            return

        def intercepted_write(records, vals):
            Rule = records.env['approval.rule'].sudo()
            state_rules_for_model = Rule.search([
                ('model_name', '=', records._name),
                ('rule_type', '=', 'state'),
                '|', ('company_id', '=', False), ('company_id', 'in', records.env.companies.ids)
            ])

            if state_rules_for_model:
                unique_state_fields = state_rules_for_model.mapped('state_field_name')
                records_to_process = records
                for state_field_name in unique_state_fields:
                    new_state = vals.get(state_field_name)
                    if new_state is None:
                        continue
                    for rec in records_to_process:
                        rules = Rule._get_ordered_rules(
                            model_name=records._name,
                            trigger_type='state',
                            state_field_name=state_field_name,
                            trigger_value=new_state
                        )
                        if not rules:
                            continue

                        Request = rec.env['approval.request'].sudo()
                        next_rule_to_approve = None
                        for rule in rules:
                            if not rule._match_record(rec):
                                continue
                            pending = rule._get_cycle_requests(
                                rec._name, rec.id).filtered(
                                lambda req: req.state == 'pending')
                            if pending:
                                raise ValidationError(_(
                                    "Approval '%(rule)s' is pending at "
                                    "%(level)s."
                                ) % {'rule': rule.name,
                                     'level': pending[0].level_name})
                            if not rule._get_pending_level(rec._name, rec.id):
                                continue
                            next_rule_to_approve = rule
                            break

                        if next_rule_to_approve:
                            if not rec.x_is_state_approval:
                                rec.sudo().write({
                                    'x_is_state_approval': True,
                                })
                                records_to_process = records_to_process - rec
                                continue
                            if rec.x_is_state_approval:
                                raise ValidationError(
                                    _("Approval required for '%s'. Use 'Request Approval'.")
                                    % next_rule_to_approve.name
                                )
                        rule_ids = rules.mapped('id')
                        if rule_ids:
                            Request.search([
                                ('rule_id', 'in', rule_ids),
                                ('res_model', '=', rec._name),
                                ('res_id', '=', rec.id),
                                ('state', '=', 'approved'),
                            ]).sudo().write({'is_used': True})
                if records_to_process:
                    return original_write(records_to_process, vals)
                return True

            return original_write(records, vals)

        intercepted_write._approval_interceptor = True
        setattr(model.__class__, 'write', intercepted_write)

    def action_sync_buttons(self):
        self.env['ir.buttons'].load_buttons_from_views(self.model_id)


class ApprovalRuleLine(models.Model):
    _name = 'approval.rule.line'
    _description = 'Approval Level'
    _order = 'sequence, id'

    rule_id = fields.Many2one(
        'approval.rule',
        string='Approval Rule',
        required=True,
        ondelete='cascade',
        index=True,
    )
    sequence = fields.Integer(
        default=10,
        help="Order of this level. The lowest sequence is requested first and "
             "the next level is only requested once it has been approved."
    )
    name = fields.Char(
        string='Description',
        help="Optional label for this level, e.g. 'Manager' or 'Finance'."
    )
    level = fields.Integer(
        string='Level',
        compute='_compute_level',
        help="Position of this level in the approval chain."
    )
    user_id = fields.Many2one(
        'res.users',
        string='Approver',
        help="The user who has to approve at this level.",
        domain=[("share", "=", False)]
    )
    group_id = fields.Many2one(
        'res.groups',
        string='Approver Group',
        help="Any member of this group can approve at this level."
    )
    approver_name = fields.Char(
        compute='_compute_approver_name',
        help="Approver or approver group of this level."
    )
    company_id = fields.Many2one(
        related='rule_id.company_id',
        store=True,
        index=True,
    )
    request_ids = fields.One2many(
        'approval.request',
        'line_id',
        string='Requests',
        help="Approval requests created for this level."
    )

    @api.constrains('user_id', 'group_id')
    def _constraint_approver(self):
        for line in self:
            if not line.user_id and not line.group_id:
                raise ValidationError(_(
                    "Each approval level needs an approver or an approver "
                    "group."
                ))

    @api.depends('rule_id.approval_line_ids', 'sequence')
    def _compute_level(self):
        for line in self:
            siblings = line.rule_id.approval_line_ids.sorted(level_sort_key)
            line.level = list(siblings).index(line) + 1 if line in siblings else 1

    @api.depends('user_id', 'group_id')
    def _compute_approver_name(self):
        for line in self:
            line.approver_name = line.user_id.display_name or \
                line.group_id.display_name or _('Undefined')

    @api.depends('name', 'sequence', 'user_id', 'group_id')
    def _compute_display_name(self):
        for line in self:
            label = line.name or _('Level %s') % line.level
            line.display_name = '%s - %s' % (label, line.approver_name)


class ApprovalStateValue(models.Model):
    """Helper model to represent many2one state values like ir.model.fields.selection"""
    _name = 'approval.state.value'
    _description = 'Approval State Value (Many2one)'
    _rec_name = 'name'

    res_model = fields.Char(string='Model', required=True, index=True)
    res_id = fields.Integer(string='Record ID', required=True, index=True)
    name = fields.Char(string='Display Name', required=True)

    _sql_constraints = [
        ('unique_model_id', 'UNIQUE(res_model, res_id)',
         'Only one state value per model record allowed!')
    ]

    @api.depends('name')
    def _compute_display_name(self):
        """Display the actual record name in the dropdown"""
        for rec in self:
            rec.display_name = rec.name
