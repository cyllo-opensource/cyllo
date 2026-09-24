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
from odoo.http import request

class IrQWeb(models.AbstractModel):
    _inherit = 'ir.qweb'

    def _get_asset_links(self, bundle, css=True, js=True, debug=None):
        """Generates asset nodes.
        If debug=assets, the assets will be regenerated when a file which composes them has been modified.
        Else, the assets will be generated only once and then stored in cache.
        """
        session = getattr(request, 'session', None)
        studio = getattr(session, 'studio', None)
        is_pdf = self.env.context.get('report_type') == 'pdf'
        rtl = self.env['res.lang'].sudo()._lang_get_direction(
            self.env.context.get('lang') or self.env.user.lang) == 'rtl'
        assets_params = self.env['ir.asset']._get_asset_params()  # website_id
        debug_assets = bool(debug and 'assets' in debug and not is_pdf)
        studio_mode = bool(studio == '1' and not is_pdf)
        if debug_assets or studio_mode:
            return self._generate_asset_links(bundle, css=css, js=js, debug_assets=debug_assets,
                                              assets_params=assets_params, rtl=rtl)
        else:
            return self._generate_asset_links_cache(bundle, css=css, js=js, assets_params=assets_params, rtl=rtl)
