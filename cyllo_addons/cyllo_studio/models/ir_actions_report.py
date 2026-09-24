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
import io
import json
import logging
import re
import werkzeug

from lxml import etree
from markupsafe import escape
from PIL import Image

from collections import OrderedDict

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.http import request
from odoo.tools import is_html_empty
from odoo.tools.pdf import PdfFileWriter, PdfFileReader
from odoo.tools.safe_eval import time


class IrActionsReport(models.Model):
    """Extension of ir.actions.report to enhance rendering and PDF handling."""
    _inherit = 'ir.actions.report'

    report_thumbnail = fields.Image("Report Thumbnail", max_width=1024, max_height=1024, attachment=True)

    @api.model
    def get_safe_image_data_uri(self, base64_source):
        """ Convert any image (including WebP/HEIC if supported by Pillow) to a safe PNG data URI for wkhtmltopdf """
        if not base64_source:
            return ''
        try:
            # base64_source can be a string or bytes
            if isinstance(base64_source, str):
                base64_source = base64_source.encode('utf-8')

            img_bytes = base64.b64decode(base64_source)
            image = Image.open(io.BytesIO(img_bytes))

            # Convert to RGBA for PNG compatibility
            if image.mode not in ('RGB', 'RGBA'):
                image = image.convert('RGBA')

            out = io.BytesIO()
            image.save(out, format='PNG')
            safe_b64 = base64.b64encode(out.getvalue()).decode('utf-8')
            return f"data:image/png;base64,{safe_b64}"
        except Exception as e:
            logging.getLogger(__name__).warning("Studio safe image conversion failed: %s", e)
            return ''

    def _get_report(self, report_ref):
        """Get the report (with sudo) from a reference
        report_ref: can be one of
            - ir.actions.report id
            - ir.actions.report record
            - ir.model.data reference to ir.actions.report
            - ir.actions.report report_name
        """
        ReportSudo = self.env['ir.actions.report'].sudo()
        if isinstance(report_ref, int):
            return ReportSudo.browse(report_ref)
        if isinstance(report_ref, models.Model):
            if report_ref._name != self._name:
                raise ValueError("Expected report of type %s, got %s" % (self._name, report_ref._name))
            return report_ref.sudo()
        report = ReportSudo.search([('report_name', '=', report_ref)], limit=1)
        if report:
            return report
        report = self.env.ref(report_ref)
        if report:
            if report._name != "ir.actions.report":
                raise ValueError("Fetching report %r: type %s, expected ir.actions.report" % (report_ref, report._name))
            return report.sudo()
        raise ValueError("Fetching report %r: report not found" % report_ref)

    def _get_studio_preview_report_block(self, report):
        """Return a structured preview block when Studio should skip rendering.

        Currently this is limited to the pricelist report so other previews keep
        their existing flow.
        """
        pricelist_report_names = {
            'product.report_pricelist',
            'product.report_pricelist_page',
        }
        if report.report_name not in pricelist_report_names and report.model != 'product.pricelist':
            return None
        if self.env.user.has_group('product.group_product_pricelist'):
            return None
        return {
            'success': False,
            'error': 'pricelist_disabled',
            'message': _(
                'Please enable Pricelists in Settings > Sales > Pricing before previewing this report.'
            ),
        }

    # Protected layout template keys — Custom_ XPath overrides on these break
    # the t-if/t-else sibling chain and cause QWebException at compile time.
    _PROTECTED_LAYOUT_KEYS = [
        'web.external_layout_standard',
        'web.external_layout_boxed',
        'web.external_layout_bold',
        'web.external_layout_striped',
        'web.external_layout',
        'web.html_container',
        'web.basic_layout',
        'web.internal_layout',
        'web.address_layout',
    ]

    def _purge_broken_layout_views(self):
        """Remove any Custom_ inherited views on protected layout templates.
        These cause QWebException: t-elif must be preceded by t-if/t-elif.
        Returns number of views removed."""
        removed = 0
        for key in self._PROTECTED_LAYOUT_KEYS:
            base_view = self.env.ref(key, raise_if_not_found=False)
            if not base_view:
                continue
            broken = self.env['ir.ui.view'].sudo().search([
                ('inherit_id', '=', base_view.id),
                '|', ('name', 'like', 'Custom_'), ('key', 'like', 'Custom_'),
            ])
            if broken:
                import logging
                _logger = logging.getLogger(__name__)
                _logger.warning(
                    "[Cyllo Studio] Purging %d broken Custom_ view(s) on protected layout %r: %s",
                    len(broken), key, broken.mapped('name')
                )
                broken.sudo().unlink()
                removed += len(broken)
        return removed

    def _render_template(self, template, values=None):
        """Allow to render a QWeb template python-side. This function returns the 'ir.ui.view'
        render but embellish it with some variables/methods used in reports.
        :param values: additional methods/variables used in the rendering
        :returns: html representation of the template2
        :rtype: bytes
        """
        if values is None:
            values = {}

        # Browse the user instead of using the sudo self.env.user
        user = self.env['res.users'].browse(self.env.uid)
        view_obj = self.env['ir.ui.view'].with_context(inherit_branding=False)
        values.update(
            time=time,
            context_timestamp=lambda t: fields.Datetime.context_timestamp(self.with_context(tz=user.tz), t),
            user=user,
            res_company=self.env.company,
            web_base_url=self._get_report_url(),
            url_quote=werkzeug.urls.url_quote,
        )
        try:
            return view_obj._render_template(template, values).encode()
        except Exception as e:
            # Self-healing: if the error looks like a broken t-if/t-else chain caused by
            # a Custom_ view being injected into a protected layout template, purge those
            # broken views and retry once.
            err_str = str(e)
            if ('t-elif directive must be preceded by t-if' in err_str
                    or 't-else directive must be preceded by t-if' in err_str):
                removed = self._purge_broken_layout_views()
                if removed:
                    # Invalidate QWeb cache so the purged views are not reused
                    self.env['ir.qweb'].sudo().clear_caches()
                    return view_obj._render_template(template, values).encode()
            raise

    def _render_qweb_html(self, report_ref, docids, data=None):
        """Render QWeb report to HTML."""
        if not data:
            data = {}
        data.setdefault('report_type', 'html')
        self = self.with_context(report_type=data.get('report_type'))
        report = self._get_report(report_ref)

        data = self._get_rendering_context(report, docids, data)
        return self._render_template(report.report_name, data), 'html'

    def _get_report_url(self, layout=None):
        """Use the active request host for Studio PDFs.

        Studio preview loads reports from the browser's current host. If
        wkhtmltopdf uses a stale ``report.url``/``web.base.url`` instead, it can
        fetch missing CSS/images and produce an unstyled PDF or
        ``ContentNotFoundError``.
        """
        if self.env.context.get('cyllo_studio_pdf') and request and request.httprequest:
            return request.httprequest.host_url.rstrip('/')
        return self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        # if self.env.context.get('cyllo_studio_pdf') and request and request.httprequest:
        #     return request.httprequest.host_url.rstrip('/')
        # return super()._get_report_url(layout=layout)

    def _render_qweb_pdf_prepare_streams(self, report_ref, data, res_ids=None):
        """Prepare and split PDF streams for the given report."""
        if not data:
            data = {}
        data.setdefault('report_type', 'pdf')

        # access the report details with sudo() but evaluation context as current user
        report_sudo = self._get_report(report_ref)
        has_duplicated_ids = res_ids and len(res_ids) != len(set(res_ids))

        collected_streams = OrderedDict()

        # Fetch the existing attachments from the database for later use.
        # Reload the stream from the attachment in case of 'attachment_use'.
        if res_ids:
            records = self.env[report_sudo.model].browse(res_ids)
            for record in records:
                res_id = record.id
                if res_id in collected_streams:
                    continue

                stream = None
                attachment = None
                if not has_duplicated_ids and report_sudo.attachment and not self._context.get(
                        "report_pdf_no_attachment"):
                    attachment = report_sudo.retrieve_attachment(record)

                    # Extract the stream from the attachment.
                    if attachment and report_sudo.attachment_use:
                        stream = io.BytesIO(attachment.raw)

                        # Ensure the stream can be saved in Image.
                        if attachment.mimetype.startswith('image'):
                            img = Image.open(stream)
                            new_stream = io.BytesIO()
                            img.convert("RGB").save(new_stream, format="pdf")
                            stream.close()
                            stream = new_stream

                collected_streams[res_id] = {
                    'stream': stream,
                    'attachment': attachment,
                }

        # Call 'wkhtmltopdf' to generate the missing streams.
        res_ids_wo_stream = [res_id for res_id, stream_data in collected_streams.items() if not stream_data['stream']]
        all_res_ids_wo_stream = res_ids if has_duplicated_ids else res_ids_wo_stream
        is_whtmltopdf_needed = not res_ids or res_ids_wo_stream

        if is_whtmltopdf_needed:

            if self.get_wkhtmltopdf_state() == 'install':
                # wkhtmltopdf is not installed
                # the call should be catched before (cf /report/check_wkhtmltopdf) but
                # if get_pdf is called manually (email template), the check could be
                raise UserError(_("Unable to find Wkhtmltopdf on this system. The PDF can not be created."))

            # Disable the debug mode in the PDF rendering in order to not split the assets bundle
            # into separated files to load. This is done because of an issue in wkhtmltopdf
            # failing to load the CSS/Javascript resources in time.
            # Without this, the header/footer of the reports randomly disappear
            # because the resources files are not loaded in time.
            # https://github.com/wkhtmltopdf/wkhtmltopdf/issues/2083
            additional_context = {'debug': False, 'report_type': 'pdf'}

            html = \
                self.with_context(**additional_context)._render_qweb_html(report_ref, all_res_ids_wo_stream, data=data)[
                    0]

            bodies, html_ids, header, footer, specific_paperformat_args = self.with_context(
                **additional_context)._prepare_html(html, report_model=report_sudo.model)

            if not has_duplicated_ids and report_sudo.attachment and set(res_ids_wo_stream) != set(html_ids):
                raise UserError(_(
                    "The report's template %r is wrong, please contact your administrator. \n\n"
                    "Can not separate file to save as attachment because the report's template does not contains the"
                    " attributes 'data-oe-model' and 'data-oe-id' on the div with 'article' classname.",
                    report_sudo.name,
                ))

            pdf_content = self._run_wkhtmltopdf(
                bodies,
                report_ref=report_ref,
                header=header,
                footer=footer,
                landscape=self._context.get('landscape'),
                specific_paperformat_args=specific_paperformat_args,
                set_viewport_size=self._context.get('set_viewport_size'),
            )
            pdf_content_stream = io.BytesIO(pdf_content)

            # Printing a PDF report without any records. The content could be returned directly.
            if has_duplicated_ids or not res_ids:
                return {
                    False: {
                        'stream': pdf_content_stream,
                        'attachment': None,
                    }
                }

            # Split the pdf for each record using the PDF outlines.

            # Only one record: append the whole PDF.
            if len(res_ids_wo_stream) == 1:
                collected_streams[res_ids_wo_stream[0]]['stream'] = pdf_content_stream
                return collected_streams

            # In case of multiple docs, we need to split the pdf according the records.
            # In the simplest case of 1 res_id == 1 page, we use the PDFReader to print the
            # pages one by one.
            html_ids_wo_none = [x for x in html_ids if x]
            reader = PdfFileReader(pdf_content_stream)
            if reader.numPages == len(res_ids_wo_stream):
                for i in range(reader.numPages):
                    attachment_writer = PdfFileWriter()
                    attachment_writer.addPage(reader.getPage(i))
                    stream = io.BytesIO()
                    attachment_writer.write(stream)
                    collected_streams[res_ids_wo_stream[i]]['stream'] = stream
                return collected_streams

            # In cases where the number of res_ids != the number of pages,
            # we split the pdf based on top outlines computed by wkhtmltopdf.
            # An outline is a <h?> html tag found on the document. To retrieve this table,
            # we look on the pdf structure using pypdf to compute the outlines_pages from
            # the top level heading in /Outlines.
            if len(res_ids_wo_stream) > 1 and set(res_ids_wo_stream) == set(html_ids_wo_none):
                root = reader.trailer['/Root']
                has_valid_outlines = '/Outlines' in root and '/First' in root['/Outlines']
                if not has_valid_outlines:
                    return {False: {
                        'report_action': self,
                        'stream': pdf_content_stream,
                        'attachment': None,
                    }}

                outlines_pages = []
                node = root['/Outlines']['/First']
                while True:
                    outlines_pages.append(root['/Dests'][node['/Dest']][0])
                    if '/Next' not in node:
                        break
                    node = node['/Next']
                outlines_pages = sorted(set(outlines_pages))

                # The number of outlines must be equal to the number of records to be able to split the document.
                has_same_number_of_outlines = len(outlines_pages) == len(res_ids_wo_stream)

                # There should be a top-level heading on first page
                has_top_level_heading = outlines_pages[0] == 0

                if has_same_number_of_outlines and has_top_level_heading:
                    # Split the PDF according to outlines.
                    for i, num in enumerate(outlines_pages):
                        to = outlines_pages[i + 1] if i + 1 < len(outlines_pages) else reader.numPages
                        attachment_writer = PdfFileWriter()
                        for j in range(num, to):
                            attachment_writer.addPage(reader.getPage(j))
                        stream = io.BytesIO()
                        attachment_writer.write(stream)
                        collected_streams[res_ids_wo_stream[i]]['stream'] = stream

                    return collected_streams

            collected_streams[False] = {'stream': pdf_content_stream, 'attachment': None}

        return collected_streams

    def _get_rendering_context(self, report, docids, data):
        """Build and return rendering context for a report."""
        # If the report is using a custom model to render its html, we must use it.
        # Otherwise, fallback on the generic html rendering.
        report_model = self._get_rendering_context_model(report)

        data = data and dict(data) or {}

        # ── Studio Preview Hack ──────────────────────────────────────────────
        # AbstractModel reports (like financial reports) usually expect 'data'
        # from a wizard. In Studio preview, data only contains 'report_type'.
        if report_model is not None:
            is_studio_preview = not data or set(data.keys()) <= {'report_type', 'context', 'discard_logo_check'}
            if is_studio_preview:
                from datetime import date
                from dateutil.relativedelta import relativedelta
                today = date.today()
                start_of_month = today.replace(day=1)
                end_of_month = (start_of_month + relativedelta(months=1)) - relativedelta(days=1)
                start_date_str = start_of_month.strftime('%Y-%m-%d')
                end_date_str = end_of_month.strftime('%Y-%m-%d')
                today_str = today.strftime('%Y-%m-%d')

                company_ids = self.env.company.ids

                # Defaults for Aged Receivable
                if 'aged_receivable' in report.report_name:
                    data.update({
                        'partners': [],
                        'date': today_str,
                        'company_ids': company_ids,
                        'account_type': 'asset_receivable',
                        'report_name': report.name,
                    })
                # Defaults for Aged Payable
                elif 'aged_payable' in report.report_name:
                    data.update({
                        'partners': [],
                        'date': today_str,
                        'company_ids': company_ids,
                        'account_type': 'liability_payable',
                        'report_name': report.name,
                    })
                # Defaults for Partner Ledger
                elif 'partner_ledger' in report.report_name:
                    data.update({
                        'partner_id': docids or [],
                        'startDate': start_date_str,
                        'endDate': end_date_str,
                        'parent_state': None,
                        'account_type': [],
                        'report_name': report.name,
                        'company_id': company_ids,
                    })
                # Defaults for Bank Book
                elif 'report_bank_book' in report.report_name:
                    data.update({
                        'partners': [],
                        'startDate': start_date_str,
                        'endDate': end_date_str,
                        'accounts': [],
                        'parent_state': ['posted'],
                        'account_type': 'bank',
                        'report_name': report.name,
                    })
                # Defaults for Cash Book
                elif 'report_cash_book' in report.report_name:
                    data.update({
                        'partners': [],
                        'startDate': start_date_str,
                        'endDate': end_date_str,
                        'accounts': [],
                        'parent_state': ['posted'],
                        'account_type': 'cash',
                        'report_name': report.name,
                    })
                # Defaults for General Ledger
                elif 'general_ledger' in report.report_name:
                    data.update({
                        'journal_ids': [],
                        'analytic_ids': [],
                        'target_move': ['posted'],
                        'start_date': start_date_str,
                        'end_date': end_date_str,
                        'filter_type': 'month',
                        'get_filters': True,
                    })
                # Defaults for Tax Report
                elif 'tax_report' in report.report_name:
                    data.update({
                        'report_name': report.name,
                        'period_data': [f"{start_date_str} to {end_date_str}"],
                        'filters': {
                            'startDate': start_date_str,
                            'endDate': end_date_str,
                            'options': ['posted', 'draft'],
                            'company': self.env.company.ids,
                            'report_type': 'generic',
                        },
                        'args': [1, 'month'],
                    })
                # Defaults for PNL / Balance Sheet / Trial Balance
                elif 'profit_n_loss' in report.report_name or 'balance_sheet' in report.report_name or 'trial_balance' in report.report_name:
                    data.update({
                        'reportName': report.name,
                        'filterBy': '',
                        'periods': {},
                        'filterData': {
                            'start_date': start_date_str,
                            'end_date': end_date_str,
                            'journal_ids': [],
                            'account_ids': [],
                            'analytic_ids': [],
                            'target_move': ['posted', 'draft'],
                            'comparison_value': 1,
                            'comparison_type_value': 'month',
                            'options': ['posted', 'draft'],
                        }
                    })

        if report_model is not None:
            # Call the custom model to get values
            res_values = report_model._get_report_values(docids, data=data)

            data.update(res_values)
        else:
            docs = self.env[report.model].browse(docids)
            data.update({
                'doc_ids': docids,
                'doc_model': report.model,
                'docs': docs,
            })
        data['is_html_empty'] = is_html_empty
        return data

    def get_values(self):
        """Return metadata of available reports."""
        reports = self.search([])
        # NB: return ``model_id`` as an int id — a Many2one recordset is not
        # JSON-serializable and broke this method over jsonrpc. The previous
        # ``for test in reports`` loop searched a non-stored field, overwrote
        # its result each iteration and used it nowhere, so it was removed.
        return [{'id': rec.id, 'name': rec.name, 'model_id': rec.model_id.id, 'model': rec.model,
                 'report_name': rec.report_name} for rec in reports]

    @api.model
    def get_qweb(self, data):
        """Return QWeb templates related to a report."""
        qweb_code = self.env['ir.ui.view'].search(
            [('name', 'ilike', data['report_name'].split('.')[1]), ('type', '=', 'qweb')])
        return [{'arch': views.arch} for views in qweb_code]

    # studio report testing from here
    def get_custom_report_page(self):
        report = self.report_name.strip()
        view = self.env.ref(report)
        arch = view.get_iframe_rendered_template(report)
        return {
            'type': 'ir.actions.client',
            'tag': 'edit_report',
            'params': {
                'report_id': self.id,
                'model_id': self.binding_model_id.id,
                'res_model': self.model,
                'template': report,
                'arch': arch,
                'has_thumbnail': bool(self.report_thumbnail),
            }
        }

    @api.model
    def action_create_blank_report(self, name, model_id, template_id=False):
        """Create a new blank report and its corresponding QWeb view."""
        self = self.sudo()
        model_rec = self.env['ir.model'].browse(int(model_id))
        if not model_rec:
            return {'success': False, 'error': 'Model not found'}

        # Nuclear Cleanup: Remove any inherited views that might be blocking the system
        # (specifically those targeting the Studio editor or common layouts that are broken)
        # Scope the match to inherited qweb views that actually carry these paths as an
        # xpath *expression* (expr="..."). The previous domain matched the raw substring
        # anywhere in arch_db and was unscoped, so any unrelated view whose stored arch
        # happened to contain the substring would be unlinked (DB-wide data loss).
        broken_xpaths = ['/t/div[1]/div[3]/div/ul/div[1]/div', '/t/div[1]/div[3]/div/ul']
        for xpath in broken_xpaths:
            bad_views = self.env['ir.ui.view'].search([
                ('type', '=', 'qweb'),
                ('inherit_id', '!=', False),
                ('arch_db', 'like', f'expr="{xpath}"'),
            ])
            if bad_views:
                bad_views.sudo().unlink()

        # Also purge anything inheriting from the Studio editor itself, just in case
        editor_view = self.env.ref('cyllo_studio.edit_report', raise_if_not_found=False)
        if not editor_view:
            editor_view = self.env['ir.ui.view'].search([('name', '=', 'edit_report')], limit=1)
        if editor_view:
            orphans = self.env['ir.ui.view'].search([('inherit_id', '=', editor_view.id)])
            if orphans:
                orphans.sudo().unlink()

        # Unique identifier using timestamp
        identifier = str(fields.Datetime.now().timestamp()).replace('.', '_')
        report_key = f"studio_report_{identifier}"
        xml_id = f"cyllo_studio_custom.{report_key}"

        template_record = self.env['cyllo.report.template'].browse(int(template_id)) if template_id else False
        template_payload = {}
        if template_record and template_record.exists():
            try:
                template_payload = json.loads(template_record.payload_json or '{}')
            except Exception:
                template_payload = {}

        # Create the QWeb view with a basic blank structure, or reuse a saved template structure.
        view_arch = f"""
            <t t-name="{xml_id}">
                <t t-call="web.html_container">
                    <t t-call="web.external_layout">
                        <t t-foreach="docs" t-as="doc">
                            <div class="page">
                                <div class="oe_structure"/>
                                <div class="row">
                                    <div class="col-12">
                                        <h2 class="text-center mt-4">{escape(name)}</h2>
                                        <p class="text-muted text-center">New Report for {escape(model_rec.name)}</p>
                                    </div>
                                </div>
                                <div class="oe_structure"/>
                            </div>
                        </t>
                    </t>
                </t>
            </t>
        """
        template_arch = template_payload.get('architecture', {}).get('document_arch') if template_payload else ''
        if template_arch:
            try:
                root = etree.fromstring(template_arch.encode('utf-8'))
                root.set('t-name', xml_id)
                view_arch = etree.tostring(root, encoding='unicode', pretty_print=True)
            except Exception:
                view_arch = template_arch
                view_arch = re.sub(r't-name="[^"]+"', f't-name="{xml_id}"', view_arch, count=1)
                view_arch = re.sub(r"t-name='[^']+'", f"t-name='{xml_id}'", view_arch, count=1)

        view = self.env['ir.ui.view'].create({
            'name': name,
            'type': 'qweb',
            'arch': view_arch,
            'key': xml_id,
        })

        # Create ir.model.data so env.ref works
        self.env['ir.model.data'].create({
            'name': report_key,
            'module': 'cyllo_studio_custom',
            'model': 'ir.ui.view',
            'res_id': view.id,
            'noupdate': True,
        })

        report_values = {
            'name': name,
            'model': model_rec.model,
            'report_type': 'qweb-pdf',
            'report_name': xml_id,
            'report_file': xml_id,
            'binding_model_id': model_rec.id,
            'binding_type': 'report',
        }
        if template_payload:
            page_settings = template_payload.get('page_settings', {})
            visibility_settings = template_payload.get('visibility_settings', {})
            paperformat_id = page_settings.get('paperformat_id')
            if paperformat_id and self.env['report.paperformat'].browse(int(paperformat_id)).exists():
                report_values['paperformat_id'] = int(paperformat_id)
            report_values['attachment_use'] = bool(visibility_settings.get('attachment_use'))
            if visibility_settings.get('print_report_name'):
                report_values['print_report_name'] = visibility_settings.get('print_report_name')

        # Create the report action
        report_action = self.create(report_values)

        # Return the studio editor action for the new report
        return report_action.get_custom_report_page()
