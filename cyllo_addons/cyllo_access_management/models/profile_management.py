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
from odoo import _, api, fields, models


class ProfileManagement(models.Model):
    _name = 'profile.management'
    _description = 'Profile Management'
    _inherit = 'mail.thread'

    name = fields.Char(
        'Name',
        required=True,
        tracking=True,
        help="Descriptive name of the profile management record."
    )
    company_ids = fields.Many2many(
        'res.company',
        string='Companies',
        help="Optional companies this profile management rule applies to "
             "(leave empty for all)."
    )
    profile_ids = fields.Many2many(
        'user.profile',
        string='Profiles',
        required=True,
        help="User profiles that will inherit these configuration rules."
    )
    is_readonly = fields.Boolean(
        'Profile System Readonly',
        help="Make the entire system read-only for users with this profile."
    )
    disable_chatter = fields.Boolean(
        'Disable Chatter',
        help="Disable chatter and messaging logs on all document views."
    )
    disable_debug_mode = fields.Boolean(
        'Disable Debug Mode',
        help="Prevent users from activating developer debug modes."
    )
    disable_login = fields.Boolean(
        'Disable Login',
        help="Prevent users in this profile from logging into the database."
    )
    menu_ids = fields.Many2many(
        'ir.ui.menu',
        string='Menus',
        help="Restrict and hide specific menu items from users."
    )
    hide_buttons_tabs_ids = fields.One2many(
        'hide.buttons.tabs',
        'profile_management_id',
        string='Hide Buttons and Tabs',
        help="Rules to hide specific XML buttons and tabs."
    )
    hide_filters_ids = fields.One2many(
        'hide.filters',
        'profile_management_id',
        string='Hide Filters and Groups',
        help="Rules to hide specific search view filters and grouping choices."
    )
    field_access_ids = fields.One2many(
        'field.access',
        'profile_management_id',
        string='Field Access',
        help="Rules to customize field-level permissions "
             "(readonly, required, invisible, links)."
    )
    model_access_ids = fields.One2many(
        'model.access',
        'profile_management_id',
        string='Model Access',
        help="Rules to customize model-level permissions "
             "(readonly, hide create/edit/delete/export/duplicate/actions)."
    )
    domain_access_ids = fields.One2many(
        'domain.access',
        'profile_management_id',
        string='Domain Access',
        help="Rules to apply conditional record-level filtering domains."
    )
    access_count = fields.Integer(
        '# Access Rights',
        compute='_compute_accesses_count',
        compute_sudo=True,
        help='Number of access rights that apply to the current user profile.'
    )
    rule_count = fields.Integer(
        '# Record Rules',
        compute='_compute_accesses_count',
        compute_sudo=True,
        help='Number of record rules that apply to the current profile '
             'management.'
    )
    user_count = fields.Integer(
        '# Users',
        compute='_compute_user_count',
        help='Number of users that apply to the current user profile '
             'management.'
    )
    is_activated = fields.Boolean(
        'Active',
        default=True,
        help="Enable or disable this profile management rule."
    )

    @api.depends('profile_ids')
    def _compute_accesses_count(self):
        """Compute the number of access rights and record rules."""
        for record in self:
            groups = record.profile_ids.group_ids
            record.access_count = len(groups.model_access)
            record.rule_count = len(groups.rule_groups)

    @api.depends('profile_ids')
    def _compute_user_count(self):
        """Compute the number of users assigned to the profiles."""
        for record in self:
            users = record.profile_ids.user_ids
            record.user_count = len(users)

    def action_show_users(self):
        """Open the users associated with the selected profiles."""
        self.ensure_one()
        return {
            'name': 'Users',
            'view_mode': 'tree,form',
            'res_model': 'res.users',
            'type': 'ir.actions.act_window',
            'context': {'create': False, 'delete': False},
            'domain': [('id', 'in', self.profile_ids.user_ids.ids)],
            'target': 'current',
        }

    def action_show_access_rights(self):
        """Open the access rights associated with the selected profiles."""
        self.ensure_one()
        return {
            'name': 'Access Rights',
            'view_mode': 'tree,form',
            'res_model': 'ir.model.access',
            'type': 'ir.actions.act_window',
            'context': {'create': False, 'delete': False},
            'domain': [
                ('id', 'in', self.profile_ids.group_ids.model_access.ids)
            ],
            'target': 'current',
        }

    def action_show_record_rules(self):
        """Open the record rules associated with the selected profiles."""
        self.ensure_one()
        return {
            'name': 'Record Rules',
            'view_mode': 'tree,form',
            'res_model': 'ir.rule',
            'type': 'ir.actions.act_window',
            'context': {'create': False, 'delete': False},
            'domain': [
                ('id', 'in', self.profile_ids.group_ids.rule_groups.ids)
            ],
            'target': 'current',
        }

    def action_refresh_ui_components(self):
        """Refresh UI components and display a success notification."""
        self._load_ui_components()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'message': _(
                    'Buttons, tabs, filters, and groups refreshed.'
                ),
                'sticky': False,
            },
        }

    @api.model
    def _load_ui_components(self):
        """Load buttons, tabs, and filters from XML views."""
        self.env['ir.buttons'].sudo().load_buttons_from_views()
        self.env['ir.tabs'].sudo().load_tabs_from_views()
        self.env['ir.ui.filters'].sudo().load_filters_from_views()
        return True

    @api.model
    def get_profile_flags(self, model):
        """Return profile-based UI restrictions for the given model."""
        user = self.env.user
        profiles = user.sudo().profile_ids
        company_id = self.env.company.id
        actions = []
        hide_print = False
        hide_action = False
        if profiles and not (user.has_group('base.group_system') or user.has_group('base.group_erp_manager')):
            access_mgmt = self.sudo().search([
                ('profile_ids', 'in', profiles.ids),
                ('is_activated', '=', True),
                '|',
                ('company_ids', 'in', [company_id]),
                ('company_ids', '=', False),
            ])

            if access_mgmt:
                model_rules = access_mgmt.model_access_ids.filtered(
                    lambda rule: rule.model_id.model == model
                )
                if any(model_rules.mapped('hide_archive')):
                    actions += ['archive', 'unarchive']
                if any(model_rules.mapped('hide_export')):
                    actions += ['export']
                if any(model_rules.mapped('hide_reports')):
                    hide_print = True
                if any(model_rules.mapped('hide_actions')):
                    hide_action = True
        return {
            'actions': actions,
            'hide_print': hide_print,
            'hide_actions': hide_action,
        }
