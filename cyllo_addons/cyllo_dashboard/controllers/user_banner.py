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
from odoo.http import Controller, request, route

class UserBannerController(Controller):

    @route('/user/upload_banner', type='json', auth='user', csrf=False)
    def upload_banner(self, banner_data=False):
        try:
            if not banner_data:
                return {"success": False, "error": "No data provided"}
            user = request.env.user
            user.sudo().write({'banner_image': banner_data})
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
