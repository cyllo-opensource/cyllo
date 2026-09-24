# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cyllo(<https://www.cyllo.com>)
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
from odoo import http
from odoo.http import request


class ReportThumbnailController(http.Controller):

    def _check_studio_user(self):
        """Ensure the caller is a Cyllo Studio user, consistent with the other
        studio controllers. These endpoints write report_thumbnail (sudo) and
        can trigger a sudo PDF render, so they must not be open to any
        authenticated user."""
        if not request.env.user.has_group('cyllo_studio.group_cyllo_studio_user'):
            from odoo.exceptions import AccessError
            from odoo import _
            raise AccessError(_("You don't have the access to this request."))

    @http.route('/cyllo_studio/save_report_thumbnail', type='json', auth='user')
    def save_report_thumbnail(self, report_id=None, report_name=None, image_base64=None, **kwargs):
        """
        Save a base64 image as the thumbnail for a specific report.
        """
        self._check_studio_user()
        if not image_base64:
            return {'success': False, 'error': 'Missing image data'}

        # Remove data:image uri prefix if present
        if 'base64,' in image_base64:
            image_base64 = image_base64.split('base64,')[1]

        Report = request.env['ir.actions.report'].sudo()
        report = False
        if report_id:
            report = Report.browse(int(report_id)).exists()

        if not report and report_name:
            report = Report.search([('report_name', '=', report_name)], limit=1)

        if report:
            try:
                report.write({'report_thumbnail': image_base64})
                return {'success': True}
            except Exception as e:
                return {'success': False, 'error': str(e)}

        return {'success': False, 'error': 'Report not found'}

    @http.route('/cyllo_studio/generate_report_thumbnail', type='json', auth='user')
    def generate_report_thumbnail(self, report_id=None, record_id=None, **kwargs):
        """
        Generate a thumbnail by rendering the report PDF and converting the first page to an image.
        If record_id is not given, use any existing record of the report's model (lazy kanban call).
        """
        self._check_studio_user()
        if not report_id:
            return {'success': False, 'error': 'Missing report_id'}

        # Import PyMuPDF lazily so a missing optional dependency does not break
        # module import (which would also take down save_report_thumbnail, which
        # does not need fitz).
        try:
            import fitz
        except ImportError:
            return {'success': False, 'error': 'PyMuPDF (fitz) is not installed'}

        Report = request.env['ir.actions.report'].sudo()
        report = Report.browse(int(report_id)).exists()

        if not report:
            return {'success': False, 'error': 'Report not found'}

        if not record_id:
            if not report.model:
                return {'success': False, 'error': 'no_record'}
            sample = request.env[report.model].sudo().search([], limit=1)
            if not sample:
                return {'success': False, 'error': 'no_record'}
            record_id = sample.id

        try:
            # 1. Generate PDF using Odoo's native QWeb engine
            pdf_content, _ = report.with_context(
                report_pdf_no_attachment=True,
                cyllo_studio_pdf=True,
            )._render_qweb_pdf(report_id, [record_id])

            # 2. Convert to Image using PyMuPDF (fitz)
            doc = fitz.open("pdf", pdf_content)
            page = doc.load_page(0)

            # Scale down for thumbnail
            zoom = 0.5  # 50% scale
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False)

            # Get JPEG data
            img_data = pix.tobytes("jpeg", jpg_quality=70)

            # Encode base64
            img_base64 = base64.b64encode(img_data).decode('utf-8')

            # 3. Save to report
            report.write({'report_thumbnail': img_base64})

            return {'success': True}
        except Exception as e:
            return {'success': False, 'error': str(e)}
