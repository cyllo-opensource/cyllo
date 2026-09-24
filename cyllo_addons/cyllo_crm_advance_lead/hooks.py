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
def uninstall_hook(env):
    env['crm.lead'].sudo().search([
        ('is_advance_lead', '=', True)
    ]).unlink()
    keys_to_remove = [
        "cyllo_crm_advance_lead.create_lead_wishlist",
        "cyllo_crm_advance_lead.create_lead_abandoned_cart",
        "cyllo_crm_advance_lead.create_lead_referral",
        "cyllo_crm_advance_lead.wishlist_days",
        "cyllo_crm_advance_lead.abandoned_cart_days"
    ]
    env["ir.config_parameter"].sudo().search(
        [("key", "in", keys_to_remove)]).unlink()
