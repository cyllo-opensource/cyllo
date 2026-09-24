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
import re

from odoo.addons.base.models.assetsbundle import AssetsBundle, JavascriptAsset, XMLAsset, SassStylesheetAsset, \
    ScssStylesheetAsset, LessStylesheetAsset, StylesheetAsset
from odoo.http import request
from odoo.tools.constants import STYLE_EXTENSIONS, SCRIPT_EXTENSIONS

rx_css_import = re.compile("(@import[^;{]+;?)", re.M)
rx_preprocess_imports = re.compile(r"""(@import\s?['"]([^'"]+)['"](;?))""")
rx_css_split = re.compile(r"\/\*\! ([a-f0-9-]+) \*\/")

TRACKED_BUNDLES = ['web.assets_web']


def __init__(self, name, files, external_assets=(), env=None, css=True, js=True, debug_assets=False, rtl=False,
             assets_params=None, studio_mode=False):
    """
    :param name: bundle name
    :param files: files to be added to the bundle
    :param css: if css is True, the stylesheets files are added to the bundle
    :param js: if js is True, the javascript files are added to the bundle
    """
    active_env = request.env if env is None else env
    session = getattr(request, 'session', None)
    studio = getattr(session, 'studio', None)
    is_pdf = active_env.context.get('report_type') == 'pdf'
    studio_mode = studio == '1' and name == 'web.assets_web' and not is_pdf
    asset_paths = []
    if not studio_mode:
        ir_asset = active_env['ir.asset']
        asset_params = ir_asset._get_asset_params()
        asset_paths = ir_asset._get_asset_paths('cyllo_studio.assets_backend', asset_params)
        asset_paths = [asset[0] for asset in asset_paths]

    self.name = name
    self.env = active_env
    self.javascripts = []
    self.templates = []
    self.stylesheets = []
    self.css_errors = []
    self.files = files
    self.rtl = rtl
    self.assets_params = assets_params or {}
    self.has_css = css
    self.has_js = js
    self._checksum_cache = {}
    self.is_debug_assets = debug_assets
    self.external_assets = [
        url
        for url in external_assets
        if (css and url.rpartition('.')[2] in STYLE_EXTENSIONS) or (js and url.rpartition('.')[2] in SCRIPT_EXTENSIONS)
    ]

    # asset-wide html "media" attribute
    for f in files:
        extension = f['url'].rpartition('.')[2]
        params = {
            'url': f['url'],
            'filename': f['filename'],
            'inline': f['content'],
            'last_modified': None if self.is_debug_assets else f.get('last_modified'),
        }

        if css:
            css_params = {
                'rtl': self.rtl,
            }
            if extension == 'sass':
                if not studio_mode and params['url'] in asset_paths:
                    continue
                self.stylesheets.append(SassStylesheetAsset(self, **params, **css_params))
            elif extension == 'scss':
                if not studio_mode and params['url'] in asset_paths:
                    continue
                self.stylesheets.append(ScssStylesheetAsset(self, **params, **css_params))
            elif extension == 'less':
                if not studio_mode and params['url'] in asset_paths:
                    continue
                self.stylesheets.append(LessStylesheetAsset(self, **params, **css_params))
            elif extension == 'css':
                if not studio_mode and params['url'] in asset_paths:
                    continue
                self.stylesheets.append(StylesheetAsset(self, **params, **css_params))
        if js:
            if not studio_mode and params['url'] in asset_paths:
                continue
            if extension == 'js':
                self.javascripts.append(JavascriptAsset(self, **params))
            elif extension == 'xml':
                self.templates.append(XMLAsset(self, **params))


AssetsBundle.__init__ = __init__
