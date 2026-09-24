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
import base64
import calendar
import logging
from datetime import timedelta

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

# Technical report_name values of the cyllo_accounting financial reports.
# Unlike a normal per-record qweb-pdf report, these ignore the docids they are
# rendered with and instead read a start/end date, journals, analytic accounts
# and target-move filter from data['filterData'] (see
# cyllo_accounting/reports/report_general_ledger.py and its siblings). They are
# not tied to any single record, so they need a different rendering path than
# "render this report for record X".
FINANCIAL_REPORT_NAMES = {
    'cyllo_accounting.report_profit_n_loss',
    'cyllo_accounting.report_balance_sheet',
    'cyllo_accounting.aged_receivable',
    'cyllo_accounting.aged_payable',
    'cyllo_accounting.partner_ledger',
    'cyllo_accounting.tax_report',
    'cyllo_accounting.report_trial_balance',
    'cyllo_accounting.report_bank_book',
    'cyllo_accounting.report_cash_book',
    'cyllo_accounting.report_general_ledger',
}

DATE_PRESETS = [
    ('today', 'Today'),
    ('yesterday', 'Yesterday'),
    ('last_7_days', 'Last 7 Days'),
    ('this_week', 'This Week'),
    ('last_week', 'Last Week'),
    ('this_month', 'This Month'),
    ('last_month', 'Last Month'),
    ('this_quarter', 'This Quarter'),
    ('last_quarter', 'Last Quarter'),
    ('this_year', 'This Year'),
    ('last_year', 'Last Year'),
    ('custom', 'Custom Range'),
]

TARGET_MOVE_SELECTION = [
    ('posted', 'Posted Only'),
    ('all', 'All Entries'),
]


class WorkflowReportAttachmentMixin(models.AbstractModel):
    """
        Shared helper, reused by any workflow action node (WhatsApp, Mail, ...)
        that needs to render an ir.actions.report as a PDF and attach it to an
        outgoing message.
        """
    _name = 'workflow.report.attachment.mixin'
    _description = 'Workflow Report Attachment Helper'

    @api.model
    def _report_needs_filter_data(self, report):
        """True if `report` is one of the parameterised cyllo_accounting
        financial reports that must be rendered from filterData rather than a
        record id."""
        return bool(report) and report.report_name in FINANCIAL_REPORT_NAMES

    @api.model
    def report_requires_filter_data(self, report_id):
        """RPC-callable: tells the frontend whether to show the report-filter
        fields (date range, journals, analytics, target move) for a given
        ir.actions.report id."""
        if not report_id:
            return False
        report = self.env['ir.actions.report'].sudo().browse(report_id)
        return self._report_needs_filter_data(report) if report.exists() else False

    @api.model
    def get_financial_reports(self):
        """RPC-callable: the list of {id, name} for the known cyllo_accounting
        financial reports, used by nodes (e.g. Mail) that only offer these
        parameterised reports rather than a free report search."""
        reports = self.env['ir.actions.report'].sudo().search([
            ('report_name', 'in', sorted(FINANCIAL_REPORT_NAMES)),
        ])
        return [{'id': report.id, 'name': report.display_name} for report in reports]

    @api.model
    def _resolve_date_preset(self, preset, custom_start=None, custom_end=None):
        """Return (start_date, end_date) ISO strings for a relative date-range
        preset, computed from "today" at call time so a repeating scheduled
        workflow always covers the right period on every run."""
        today = fields.Date.context_today(self)
        preset = preset or 'last_month'

        if preset == 'custom':
            start = fields.Date.to_date(custom_start) if custom_start else today
            end = fields.Date.to_date(custom_end) if custom_end else today
            return start.isoformat(), end.isoformat()

        if preset == 'today':
            start = end = today
        elif preset == 'yesterday':
            start = end = today - timedelta(days=1)
        elif preset == 'last_7_days':
            start = today - timedelta(days=6)
            end = today
        elif preset == 'this_week':
            start = today - timedelta(days=today.weekday())
            end = start + timedelta(days=6)
        elif preset == 'last_week':
            this_week_start = today - timedelta(days=today.weekday())
            start = this_week_start - timedelta(days=7)
            end = start + timedelta(days=6)
        elif preset == 'this_month':
            start = today.replace(day=1)
            end = today.replace(day=calendar.monthrange(today.year, today.month)[1])
        elif preset == 'last_month':
            first_of_this_month = today.replace(day=1)
            end = first_of_this_month - timedelta(days=1)
            start = end.replace(day=1)
        elif preset == 'this_quarter':
            start_month = (today.month - 1) // 3 * 3 + 1
            start = today.replace(month=start_month, day=1)
            end_month = start_month + 2
            end = today.replace(month=end_month, day=calendar.monthrange(today.year, end_month)[1])
        elif preset == 'last_quarter':
            this_quarter_start_month = (today.month - 1) // 3 * 3 + 1
            this_quarter_start = today.replace(month=this_quarter_start_month, day=1)
            end = this_quarter_start - timedelta(days=1)
            start_month = (end.month - 1) // 3 * 3 + 1
            start = end.replace(month=start_month, day=1)
        elif preset == 'this_year':
            start = today.replace(month=1, day=1)
            end = today.replace(month=12, day=31)
        elif preset == 'last_year':
            start = today.replace(year=today.year - 1, month=1, day=1)
            end = today.replace(year=today.year - 1, month=12, day=31)
        else:
            start = end = today

        return start.isoformat(), end.isoformat()

    @api.model
    def _build_financial_report_data(self, report, report_filters):
        """Build the `data` payload cyllo_accounting's financial reports expect
        in place of docids (see FINANCIAL_REPORT_NAMES)."""
        report_filters = report_filters or {}
        start_date, end_date = self._resolve_date_preset(
            report_filters.get('date_preset'),
            report_filters.get('start_date'),
            report_filters.get('end_date'),
        )
        journal_ids = [
            (journal.get('id') if isinstance(journal, dict) else journal)
            for journal in (report_filters.get('journal_ids') or [])
        ]
        analytic_ids = [
            (analytic.get('id') if isinstance(analytic, dict) else analytic)
            for analytic in (report_filters.get('analytic_ids') or [])
        ]
        target_move = (
            ['posted'] if (report_filters.get('target_move') or 'posted') == 'posted'
            else ['posted', 'draft']
        )
        return {
            'reportName': report.print_report_name or report.name,
            'filterData': {
                'start_date': start_date,
                'end_date': end_date,
                'journal_ids': [journal_id for journal_id in journal_ids if journal_id],
                'analytic_ids': [analytic_id for analytic_id in analytic_ids if analytic_id],
                'target_move': target_move,
                'limit': 0,
                'get_filters': False,
            },
        }

    @api.model
    def generate_report_attachment(self, report, record=None, report_filters=None):
        """
            Render `report` (a qweb-pdf ir.actions.report) and store the result as
            an ir.attachment.

            For the known cyllo_accounting financial reports, `report_filters`
            (date_preset/start_date/end_date/journal_ids/analytic_ids/target_move)
            drives the render and `record` is optional. For any other qweb-pdf
            report, `record` is required and the report is rendered the normal
            way, from that record's id.

            Returns the ir.attachment recordset, or an empty ir.attachment
            recordset if nothing could be generated.
            """
        empty = self.env['ir.attachment']
        if not report or not report.exists():
            return empty
        if report.report_type != 'qweb-pdf':
            _logger.warning(
                "Workflow report attachment: report %s is not a PDF report; skipping.",
                report.display_name,
            )
            return empty

        try:
            if self._report_needs_filter_data(report):
                data = self._build_financial_report_data(report, report_filters)
                pdf_content, _content_type = report._render_qweb_pdf(report, [], data=data)
                res_model = record._name if record else False
                res_id = record.id if record else False
                name = '%s.pdf' % (report.print_report_name or report.name)
            else:
                if not record:
                    _logger.warning(
                        "Workflow report attachment: report %s needs a source record but "
                        "none was provided; skipping.", report.display_name,
                    )
                    return empty
                pdf_content, _content_type = report._render_qweb_pdf(report, [record.id])
                res_model = record._name
                res_id = record.id
                name = '%s_%s.pdf' % (report.name, record.id)

            return self.env['ir.attachment'].sudo().create({
                'name': name,
                'type': 'binary',
                'datas': base64.b64encode(pdf_content),
                'res_model': res_model,
                'res_id': res_id,
                'mimetype': 'application/pdf',
            })
        except Exception as exc:
            _logger.error(
                "Workflow report attachment: failed to render report %s - %s",
                report.display_name, exc,
            )
            return empty
