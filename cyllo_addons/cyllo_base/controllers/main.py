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
import io
from docx import Document

from odoo.http import (Controller, content_disposition, request, route,
                       serialize_exception)
from odoo.tools import html_escape, json


class MenubarAddToShortcuts(Controller):

    @route('/menubar/add_to_shortcuts', type='json', auth='user')
    def menubar_add_to_shortcuts(self, actionId, name, actionModel, model,
                                 menu_id):
        """
            Adds a specific action identified by 'actionId' from the user's
            shortcuts.
            Parameters: actionId (int): The ID of the action to be removed from
                the user's shortcuts.
        """
        try:
            if actionModel != 'ir.actions.act_window':
                raise ValueError
            if not model:
                action = request.env[actionModel].browse(actionId)
                model = action.res_model
        except:
            return False
        isMenu = request.env['ir.ui.menu'].sudo().search_count([
            ('action', 'like', f'ir.actions.act_window,{actionId}')])
        try:
            if isinstance(menu_id, str):
                menu_id = int(menu_id.strip())
        except ValueError:
            return {'error': 'Invalid menu_id'}
        model_record = request.env['ir.model'].sudo().search(
            [('model', '=', model)], limit=1)
        if not model_record:
            return {'error': 'Model not found'}
        menu_record = request.env['ir.ui.menu'].sudo().browse(menu_id)
        if not menu_record.exists():
            return {'error': 'Menu not found'}
        path = menu_record.complete_name
        if isMenu > 0:
            if '/' in path:
                path = path.rsplit('/', 1)[0]
        request.env['shortcut.menu'].sudo().create({
            'name': name,
            'menu_id': menu_id,
            'window_action_id': actionId if actionModel == 'ir.actions.act_window' else False,
            'client_action_id': actionId if actionModel == 'ir.actions.client' else False,
            'server_action_id': actionId if actionModel == 'ir.actions.server' else False,
            'res_model': model_record.id,
            'path': path,
        })
        return True

    @route('/menubar/remove_from_shortcuts', type='json', auth='user')
    def remove_from_shortcuts(self, actionId, name, model, actionModel):
        """
            Removes a specific action identified by 'actionId' from the user's
            shortcuts.
            Parameters: actionId (int): The ID of the action to be removed from
            the user's shortcuts.
        """
        if actionModel == 'ir.actions.act_window':
            shortcut_to_remove = (request.env['shortcut.menu'].sudo().search(
                [('window_action_id', '=', actionId), ('name', '=', name)]))
        elif actionModel == 'ir.actions.server':
            shortcut_to_remove = (request.env['shortcut.menu'].sudo().search(
                [('server_action_id', '=', actionId), ('name', '=', name)]))
        else:
            shortcut_to_remove = (request.env['shortcut.menu'].sudo().search(
                [('client_action_id', '=', actionId), ('name', '=', name)]))
        shortcut_to_remove.unlink()
        return True


class DocReport(Controller):
    """Controller for handling Docx reports."""

    @route('/docx_reports', type='http', auth="public")
    def get_docx_report(self, model, options, output_format, report_name):
        """
        Generate and return a Docx report in response to an HTTP request.
        """
        uid = request.session.uid
        report_obj = request.env[model].with_user(uid)
        if output_format == 'docx':
            stream = io.BytesIO()
            document = Document()
            report_obj.get_docx_report(document, json.loads(options))
            document_file_name = report_name
            document.save(stream)
            stream.seek(0)
            return request.make_response(
                stream,
                [('Content-Type',
                  'application/vnd.openxmlformats-officedocument.wordprocessingml.document'),
                 ('Content-Disposition',
                  f'attachment; filename={document_file_name}')])


class XLSXReportController(Controller):
    """Controller for generating XLSX reports."""

    @route('/xlsx_reports', type='http', auth='user', methods=['POST'],
           csrf=False)
    def get_report_xlsx(self, model, options, output_format, report_name):
        """Generate an XLSX report based on the provided data and return it as
        a response.
            Args:
                model (str): The name of the model on which the report is based.
                options (str): The data required for generating the report.
                output_format (str): The desired output format for the report
                (e.g., 'xlsx').
                report_name (str): The name to be given to the generated report
                file.
            Returns:
                Response: The generated report file as a response.
            Raises:
                Exception: If an error occurs during report generation.
            """
        report_obj = request.env[model].with_user(request.session.uid)
        token = 'dummy-because-api-expects-one'
        try:
            if output_format == 'xlsx':
                response = request.make_response(
                    None,
                    headers=[
                        ('Content-Type', 'application/vnd.ms-excel'),
                        ('Content-Disposition',
                         content_disposition(report_name + '.xlsx'))
                    ]
                )
                report_obj.get_xlsx_report(options, response)
            response.set_cookie('fileToken', token)
            return response
        except Exception as e:
            error = {
                'code': 200,
                'message': 'Cyllo Server Error',
                'data': serialize_exception(e)
            }
            return request.make_response(html_escape(json.dumps(error)))
