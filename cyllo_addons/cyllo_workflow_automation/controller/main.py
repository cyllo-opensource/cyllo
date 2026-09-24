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
import mimetypes
import inspect
import secrets

from odoo import http
from odoo.http import request


class CylloAutoWorkController(http.Controller):

    @http.route('/cyllo_auto_work/find/functions', type="json", auth="user", csrf=False)
    def cyllo_auto_work_find_functions(self, **kwargs):
        """
            Find the methods starting with "action" on the model named in kwargs['model'].
            Returns a list of dicts with each method's name and argument names.
            """
        model = request.env[kwargs['model']]
        model_class = type(model)
        methods = []

        for attr_name in dir(model_class):
            attr = getattr(model_class, attr_name)
            if inspect.isfunction(attr) or inspect.ismethod(attr):
                if not attr_name.startswith(("__")) and attr_name.startswith("action"):
                    argspec = inspect.getfullargspec(attr)
                    method_info = {
                        'name': attr_name,
                        'args': argspec.args
                    }
                    methods.append(method_info)

        return methods

    @http.route(
        '/cyllo_workflow/upload_wa_attachment',
        type='json',
        auth='user',
        methods=['POST'],
        csrf=False,
    )
    def upload_wa_attachment(self, name, data, mimetype=None, node_struct_id=None):
        """
            Create an attachment from the WhatsApp node file uploader.
            Optionally links it to an existing node.struct record right away.
            """
        guessed_mimetype, _encoding = mimetypes.guess_type(name or '')
        attachment = request.env['ir.attachment'].sudo().create({
            'name': name,
            'type': 'binary',
            'datas': data,
            'mimetype': mimetype or guessed_mimetype or 'application/octet-stream',
        })
        if node_struct_id:
            node = request.env['node.struct'].sudo().browse(node_struct_id)
            if node.exists():
                node.write({
                    'wa_static_attachment_ids': [(4, attachment.id)],
                })
        return {
            'id': attachment.id,
            'name': attachment.name,
        }

    @http.route(
        '/cyllo_workflow/upload_mail_attachment',
        type='json',
        auth='user',
        methods=['POST'],
        csrf=False,
    )
    def upload_mail_attachment(self, name, data, mimetype=None, node_struct_id=None):
        """
            Create an attachment from the Mail node file uploader.
            Optionally links it to an existing node.struct record right away.
            """
        guessed_mimetype, _encoding = mimetypes.guess_type(name or '')
        attachment = request.env['ir.attachment'].sudo().create({
            'name': name,
            'type': 'binary',
            'datas': data,
            'mimetype': mimetype or guessed_mimetype or 'application/octet-stream',
        })
        if node_struct_id:
            node = request.env['node.struct'].sudo().browse(node_struct_id)
            if node.exists():
                node.write({
                    'mail_static_attachment_ids': [(4, attachment.id)],
                })
        return {
            'id': attachment.id,
            'name': attachment.name,
        }

    @http.route(
        '/cyllo_workflow/check_google_meet_installed',
        type='json',
        auth='user',
        methods=['POST'],
        csrf=False,
    )
    def check_google_meet_installed(self, **kwargs):
        """
            Return whether the cyllo_google_meet module is installed and its OAuth credentials are set.
            Used by the Activity node dialog to decide whether to show the Google Meet section.
        """
        installed = request.env['ir.module.module'].sudo().search_count([
            ('name', '=', 'cyllo_google_meet'),
            ('state', '=', 'installed'),
        ]) > 0
        params = request.env['ir.config_parameter'].sudo()
        configured = all([
            params.get_param('cyllo_google.client_id'),
            params.get_param('cyllo_google.client_secret'),
            params.get_param('cyllo_google.refresh_token'),
        ])
        return {
            'installed': installed,
            'configured': bool(installed and configured),
        }

    @http.route(
        '/cyllo_workflow/check_zoom_installed',
        type='json',
        auth='user',
        methods=['POST'],
        csrf=False,
    )
    def check_zoom_installed(self, **kwargs):
        """
            Return whether the cyllo_zoom module is installed and its access token is set.
            Used by the Activity node dialog to decide whether to show the Zoom Meet section.
        """
        installed = request.env['ir.module.module'].sudo().search_count([
            ('name', '=', 'cyllo_zoom'),
            ('state', '=', 'installed'),
        ]) > 0
        token = request.env['ir.config_parameter'].sudo().get_param(
            'cyllo_zoom.zoom_token',
        )
        return {
            'installed': installed,
            'configured': bool(installed and token),
        }

    @http.route(
        '/cyllo_workflow/run_now',
        type='json',
        auth='user',
        methods=['POST'],
        csrf=False,
    )
    def run_now_workflow(self, work_auto_id, **kwargs):
        """Execute a time-triggered workflow immediately for manual testing."""
        automation = request.env['work.auto'].browse(int(work_auto_id))
        if not automation.exists():
            return {'ok': False, 'error': 'Workflow not found.'}
        if automation.trigger_type != 'time':
            return {'ok': False, 'error': 'Only time-triggered workflows can be run manually.'}
        try:
            result = automation.run_now()
        except Exception as exc:
            return {'ok': False, 'error': str(exc)}
        return result

    @http.route(
        '/cyllo_workflow/test_run',
        type='json',
        auth='user',
        methods=['POST'],
        csrf=False,
    )
    def test_run_workflow(self, work_auto_id, **kwargs):
        """Validate a workflow in dry-run mode and return node-level results."""
        automation = request.env['work.auto'].browse(int(work_auto_id))
        if not automation.exists():
            return {
                'ok': False,
                'error': 'Workflow not found.',
            }
        try:
            payload = automation.dry_run()
        except Exception as exc:
            return {
                'ok': False,
                'error': str(exc),
            }
        return {
            'ok': True,
            **payload,
        }

    # ── Webhook Secret URL helpers ───────────────────────────────────────────

    @http.route(
        '/cyllo_workflow/webhook_secret_url/<int:node_id>',
        type='json',
        auth='user',
        methods=['GET', 'POST'],
        csrf=False,
    )
    def get_webhook_secret_url(self, node_id, **kwargs):
        """
        Return the current Secret URL for a given ``node.struct`` record.

        The URL is assembled at read time from the live ``web.base.url`` system
        parameter so it always reflects the current server address even when
        the base URL has been changed since the token was generated.

        Args:
            node_id (int): The database ID of the ``node.struct`` record.
            **kwargs: Unused; present for Odoo JSON-RPC compatibility.

        Returns:
            dict:
                - ``url`` (str):   The full Secret URL, or ``""`` if the node
                  has no token yet.
                - ``token`` (str): The raw secret token value.
        """
        node = request.env['node.struct'].sudo().browse(node_id)
        if not node.exists():
            return {'url': '', 'token': ''}

        token = node.webhook_secret_token or ''
        if not token:
            token = secrets.token_urlsafe(32)
            node.webhook_secret_token = token

        base_url = (
            request.env['ir.config_parameter']
            .sudo()
            .get_param('web.base.url', default='')
            .rstrip('/')
        )
        secret_url = f"{base_url}/cyllo_workflow/webhook/inbound/{token}"
        return {'url': secret_url, 'token': token}

    @http.route(
        '/cyllo_workflow/regenerate_webhook_token',
        type='json',
        auth='user',
        methods=['POST'],
        csrf=False,
    )
    def regenerate_webhook_token(self, node_struct_id, **kwargs):
        """
        Issue a brand-new secret token for the given Webhook node.

        The old token (and therefore the old Secret URL) stops working
        immediately after this call succeeds.

        Returns:
            dict: { ok: bool, url: str, token: str }  or  { ok: False, error: str }
        """
        node = request.env['node.struct'].sudo().browse(int(node_struct_id))
        if not node.exists():
            return {'ok': False, 'error': 'Node not found.'}

        token = secrets.token_urlsafe(32)
        node.write({'webhook_secret_token': token})

        base_url = request.env['ir.config_parameter'].sudo().get_param(
            'web.base.url', default='http://localhost:8069'
        ).rstrip('/')
        url = f"{base_url}/cyllo_workflow/webhook/inbound/{token}"
        return {'ok': True, 'url': url, 'token': token}

    @http.route(
        '/cyllo_workflow/webhook/inbound/<string:token>',
        type='json',
        auth='public',
        methods=['POST'],
        csrf=False,
    )
    def inbound_webhook(self, token, **kwargs):
        """
        Public inbound endpoint called by external systems.

        Looks up the node.struct by its secret token, then triggers the
        parent work.auto automation with the posted JSON payload as context.

        Returns:
            dict: { ok: bool }  or  { ok: False, error: str }
        """
        node = request.env['node.struct'].sudo().search(
            [('webhook_secret_token', '=', token)], limit=1
        )
        if not node:
            return {'ok': False, 'error': 'Invalid or expired webhook token.'}

        try:
            payload = request.get_json_data() or {}
            automation = node.work_auto_id.sudo()
            if automation.exists():
                automation.with_context(webhook_payload=payload).run_now()
        except Exception as exc:
            return {'ok': False, 'error': str(exc)}

        return {'ok': True}
