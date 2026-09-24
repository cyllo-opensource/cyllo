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
from odoo import fields, models


class AccountAnnotationMixin(models.Model):
    """
       This class represents an annotation mixin for accounting-related functionalities.

       Attributes:
           _name (str): The name of the model ('annotation.mixin').
           _description (str): A description of the model ('Account annotation mixin').
           annotations (fields.Json): A JSON field for storing annotations related to different accounting reports. The available annotations are:

               - GENERAL_LEDGER: 1
               - PARTNER_LEDGER: 2
               - AGED_RECEIVABLE: 3
               - AGED_PAYABLE: 4
               - TRIAL_BALANCE: 5
               - BALANCE_SHEET: 6
               - PROFIT_AND_LOSS: 7
               - BANK_BOOK: 8
               - CASH_BOOK: 9
               - TAX_REPORT: 10
    """
    _name = 'annotation.mixin'
    _description = 'Account annotation mixin'

    annotations = fields.Json("Annotations")

    def write_annotations(self, ledger, string_val):
        """Writes annotations based on ledger"""
        annotations = self.annotations or {}
        annotations[ledger] = string_val
        self.write({
            'annotations': annotations
        })

    def remove_annotations(self, ledger):
        """Removes annotations based on ledger"""
        annotations = self.annotations or {}
        if str(ledger) in annotations.keys():
            del annotations[str(ledger)]
            self.write({'annotations': annotations})