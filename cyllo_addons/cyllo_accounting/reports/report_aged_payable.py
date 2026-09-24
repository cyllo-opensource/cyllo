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


class ReportAgedPayable(models.AbstractModel):
    """
    Abstract model for generating an Aged Payable Report.

    This model inherits from the 'report.cyllo_accounting.aged_receivable' report.
    It defines the structure and behavior of the Aged Payable Report.

    Attributes:
        _name (str): The technical name of the model ('report.cyllo_accounting.aged_payable').
        _inherit (str): The name of the model being inherited ('report.cyllo_accounting.aged_receivable').
        _description (str): A brief description of the model ('Aged Payable Report').
    """
    _name = 'report.cyllo_accounting.aged_payable'
    _inherit = 'report.cyllo_accounting.aged_receivable'
    _description = 'Aged Payable Report'
