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
from odoo import _, api, models
from odoo.exceptions import ValidationError


class AccountMoveLine(models.Model):
    """ Inherited Account.move.line for the Analytic Distribution Checking"""
    _inherit = 'account.move.line'

    @api.constrains('analytic_distribution')
    def _check_analytic_distribution(self):
        """Constraints for checking Analytic Distribution"""
        for record in self.filtered(lambda x: x.analytic_distribution):
            analytic_distribution = [int(id_str.strip())
                                     for key in
                                     record.analytic_distribution.keys() for
                                     id_str in key.split(',')]
            for key in record.analytic_distribution.keys():
                for line in key.split(','):
                    stripped_line = line.strip()
                    if stripped_line:
                        line_analytic = self.env[
                            'account.analytic.account'].browse(
                            int(stripped_line))
                        if line_analytic.analytic_account_id and line_analytic.analytic_account_id.id in analytic_distribution:
                            raise ValidationError(
                                _(f'The {line_analytic.name} Account`s Parent'
                                  f' {line_analytic.analytic_account_id.name} '
                                  f'already included in the Analytic'
                                  f' Distribution.You can`t choose parent '
                                  f'account with child account in a same move'
                                  f' line.'))
                        elif line_analytic.analytic_account_ids:
                            for analytic_line in line_analytic.analytic_account_ids:
                                if analytic_line.id in analytic_distribution:
                                    raise ValidationError(
                                        _(f'The {line_analytic.name}'
                                          f' Account`s Child'
                                          f' {analytic_line.name} already '
                                          f'included in the Analytic '
                                          f'Distribution.You can`t choose Child '
                                          f'account with Parent account in a '
                                          f'same move line.'))
