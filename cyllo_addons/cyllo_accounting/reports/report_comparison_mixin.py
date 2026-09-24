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
from dateutil.relativedelta import relativedelta

from odoo import models
from odoo.tools import get_month


class ReportComparisonMixin(models.AbstractModel):
    """Shared helper for computing comparison-period date ranges.

    The financial reports (Profit and Loss, Balance Sheet, Trial Balance and
    Tax) all display a configurable number of comparison periods derived from
    the user's selected date range. Centralising the date shifting here keeps
    every report consistent and avoids the previously duplicated logic.
    """
    _name = 'report.comparison.mixin'
    _description = 'Financial Report Comparison Period Mixin'

    def _get_comparison_dates(self, start_date, end_date, comparison_type, count):
        """Return the ``(date_from, date_to)`` of the ``count``-th comparison period.

        The selected range is shifted backwards by ``count`` units; the unit is
        derived from the report's date filter. Month and quarter ranges are
        snapped to whole-month boundaries (matching the report filters, which
        always select full months/quarters), while custom ranges are shifted by
        their own length.

        Args:
            start_date (date): Start of the base (most recent) period.
            end_date (date): End of the base period.
            comparison_type (str): One of 'year', 'quarter', 'month' or 'custom'.
            count (int): Zero-based index of the comparison period (0 = base period).

        Returns:
            tuple(date, date): The shifted ``(date_from, date_to)``.
        """
        if comparison_type == 'year':
            date_from = start_date - relativedelta(years=count)
            date_to = end_date - relativedelta(years=count)
        elif comparison_type == 'month':
            date_from, dummy = get_month(start_date - relativedelta(months=count))
            dummy, date_to = get_month(end_date - relativedelta(months=count))
        elif comparison_type == 'quarter':
            date_from, dummy = get_month(start_date - relativedelta(months=3 * count))
            dummy, date_to = get_month(end_date - relativedelta(months=3 * count))
        else:  # custom: shift by the length of the selected range
            period_length = (end_date - start_date).days + 1
            date_from = start_date - relativedelta(days=period_length * count)
            date_to = end_date - relativedelta(days=period_length * count)
        return date_from, date_to
