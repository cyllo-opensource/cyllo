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


class IrModelAccess(models.Model):
    """Extension of ir.rule to update record rules."""
    _inherit = 'ir.rule'

    def update_record_rules(self, record_rules):
        """Update record rules with provided values."""
        for record in self:
            record_rule = next((record_data for record_data in record_rules if record_data.get('id') == record.id), None)
            if record_rule:
                record.write({
                    'name': record_rule['name'],
                    'groups': record_rule['groups'],
                    'domain_force': record_rule['domain_force'],
                    'perm_read': record_rule['perm_read'],
                    'perm_write': record_rule['perm_write'],
                    'perm_create': record_rule['perm_create'],
                    'perm_unlink': record_rule['perm_unlink']
                })
