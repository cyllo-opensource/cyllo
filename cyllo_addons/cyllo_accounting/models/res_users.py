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
from odoo import models


class ResUsers(models.Model):
    _inherit = 'res.users'

    def write(self, vals):
        readonly = self.env.ref("account.group_account_readonly", raise_if_not_found=False)
        billing = self.env.ref("account.group_account_invoice", raise_if_not_found=False)
        billing_administrator = self.env.ref("account.group_account_manager",
                                             raise_if_not_found=False)
        bookkeeper = self.env.ref("account.group_account_user", raise_if_not_found=False)

        if readonly and bookkeeper:
            readonly_set = False

            for key, val in vals.items():
                if key == (
                f'sel_groups_{readonly.id}_{billing.id}_{billing_administrator.id}') and val in [
                    readonly.id, False]:
                    readonly_set = True
                    break
                elif key == f'in_group_{readonly.id}' and val:
                    readonly_set = True
                    break
            if 'groups_id' in vals:
                for cmd in vals.get('groups_id', []):
                    if cmd[0] == 4 and cmd[1] == readonly.id:
                        readonly_set = True
                    elif cmd[0] == 6 and readonly.id in cmd[2]:
                        readonly_set = True

            if readonly_set:
                vals[f'in_group_{bookkeeper.id}'] = False
                if 'groups_id' in vals:
                    vals["groups_id"].append((3, bookkeeper.id))

        return super().write(vals)
