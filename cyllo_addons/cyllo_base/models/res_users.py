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
from odoo.exceptions import AccessDenied, UserError



class ResUsers(models.Model):
    _inherit = "res.users"

    auto_edit = fields.Boolean(
        string="Auto Edit Fields", default=True, help="Enable to make fields auto edit")
    odoobot_state = fields.Selection(string="CylloBot Status")

    @api.model
    def action_systray_view_account(self):
        """This is the action to view user form"""
        return self.sudo().env.ref('cyllo_base.action_view_my_account').read()[
            0]

    def action_reset_password(self):
        """ Allow users to reset their own password without AccessError on signup_type """
        if len(self) == 1 and self.env.user.id == self.id:
            return super(ResUsers, self.sudo()).action_reset_password()
        return super().action_reset_password()

class CheckIdentity(models.TransientModel):
    _inherit = 'res.users.identitycheck'

    def _check_identity(self):
        try:
            self.create_uid._check_credentials(
                self.password, {'interactive': True}
            )
        except AccessDenied:
            raise UserError(
                _("Incorrect Password, try again or click on Forgot Password to reset your password.")
            )
