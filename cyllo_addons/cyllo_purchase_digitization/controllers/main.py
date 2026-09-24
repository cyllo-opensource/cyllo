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
import json
import logging

# imports of odoo
from odoo import http
from odoo.http import request

logger = logging.getLogger(__name__)


class PurchaseOrderUpload(http.Controller):
    """
       HTTP Controller for uploading purchase order documents.
       """

    @http.route('/cyllo_purchase_digitization/upload_attachment',
                type='http',
                methods=['POST'],
                auth="user")
    def upload_document(self):
        """
                Handle HTTP POST request to upload purchase order document.
                :return: JSON response with the ID of the created attachment.
                """
        files = request.httprequest.files.getlist('ufile')
        for ufile in files:
            try:
                purchase_order = (request.env['purchase.order'].
                                  create([{'partner_id': 3}]))
                result = purchase_order if purchase_order else None
                mimetype = ufile.content_type
                purchase_order.message_main_attachment_id = request.env['ir.attachment'].create([
                    {'name': ufile.filename,
                     'datas': base64.encodebytes(ufile.read()),
                     'res_model': 'purchase.order',
                     'res_id': purchase_order.id,
                     'mimetype': mimetype
                     }
                ])
            except Exception as e:
                logger.exception("Fail to upload document %s" % ufile.filename)
                result = {'error': str(e)}
            return json.dumps(result.id)
