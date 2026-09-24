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
from odoo import _, models
from odoo.exceptions import ValidationError


class ResUser(models.Model):
    """Inherited module res.partner to add methods"""
    _inherit = 'res.partner'

    def unlink(self):
        """Preventing the deletion of the record which is a participant """
        records = self.env['marketing.participant'].search([])
        for rec in records:
            if rec.record_id == self.id:
                raise ValidationError(
                    _("You can not delete a partner which is a participant \n "
                      "in a Marketing Campaign"))
        return super().unlink()
