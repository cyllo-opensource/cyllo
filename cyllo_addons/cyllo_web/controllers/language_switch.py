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
from odoo import http
from odoo.http import request


class LangSwitch(http.Controller):
    """The LangSwitch class is used to change the current user's language.
    Methods:
        switch_user_lang(self, **kw):
            Getting value of the selected language and change the language in the backend.
    """
    @http.route('/lang_switch', auth='public', type='json', csrf=False)
    def switch_user_lang(self, **kw):
        """Summary: Getting value of the selected language and change the language in the backend.
        Args: kw(dict):It consists of the code of the selected language."""
        module = request.env['ir.module.module'].search([('state', '=', 'installed')])
        module._update_translations(kw['lang'], True)
        request.env.user.lang = kw['lang']
