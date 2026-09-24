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
from odoo import fields, models


class LoginUserDetail(models.Model):
    """
        Model for storing login details of users.
        This model allows you to store login details for users, including their
        username, the date and time of login (with a default value of the
        current datetime), and the IP address from which the login occurred.
    """
    _name = 'login.user.detail'
    _description = 'Login Details'

    name = fields.Char(string="User Name")
    date_time = fields.Datetime(string="Login Date And Time",
                                default=lambda self: fields.datetime.now())
    ip_address = fields.Char(string="IP Address")
    res_user_id = fields.Integer(string="User Id")
