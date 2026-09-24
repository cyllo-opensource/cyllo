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


class BalanceSheetReport(models.AbstractModel):
    """
    Abstract model for generating a Balance Sheet Report.

    This model inherits from the 'report.cyllo_accounting.report_profit_n_loss' report,
    and it defines the structure and behavior of the Balance Sheet Report.

    Attributes:
        _name (str): The technical name of the model ('report.cyllo_accounting.report_balance_sheet').
        _inherit (str): The name of the model being inherited ('report.cyllo_accounting.report_profit_n_loss').
        _description (str): A brief description of the model ('Report Cyllo Accounting Report Balance Sheet').
    """
    _name = "report.cyllo_accounting.report_balance_sheet"
    _inherit = "report.cyllo_accounting.report_profit_n_loss"
    _description = "Report Cyllo Accounting Report Balance Sheet"
    _financial_report_method = "get_balance_sheet"
