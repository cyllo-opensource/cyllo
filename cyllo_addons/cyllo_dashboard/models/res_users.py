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
import pytz
import logging

from odoo import api, fields, models, SUPERUSER_ID
from odoo.exceptions import AccessDenied,ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)

# put POSIX 'Etc/*' entries at the end to avoid confusing users - see bug 1086728

# Built once at import time instead of being rebuilt on every call/request.
_TZ_MAPPING = {
        "Africa/Asmera": "Africa/Nairobi",
        "America/Argentina/ComodRivadavia": "America/Argentina/Catamarca",
        "America/Buenos_Aires": "America/Argentina/Buenos_Aires",
        "America/Cordoba": "America/Argentina/Cordoba",
        "America/Fort_Wayne": "America/Indiana/Indianapolis",
        "America/Indianapolis": "America/Indiana/Indianapolis",
        "America/Jujuy": "America/Argentina/Jujuy",
        "America/Knox_IN": "America/Indiana/Knox",
        "America/Louisville": "America/Kentucky/Louisville",
        "America/Mendoza": "America/Argentina/Mendoza",
        "America/Rosario": "America/Argentina/Cordoba",
        "Antarctica/South_Pole": "Pacific/Auckland",
        "Asia/Ashkhabad": "Asia/Ashgabat",
        "Asia/Calcutta": "Asia/Kolkata",
        "Asia/Chungking": "Asia/Shanghai",
        "Asia/Dacca": "Asia/Dhaka",
        "Asia/Katmandu": "Asia/Kathmandu",
        "Asia/Macao": "Asia/Macau",
        "Asia/Rangoon": "Asia/Yangon",
        "Asia/Saigon": "Asia/Ho_Chi_Minh",
        "Asia/Thimbu": "Asia/Thimphu",
        "Asia/Ujung_Pandang": "Asia/Makassar",
        "Asia/Ulan_Bator": "Asia/Ulaanbaatar",
        "Atlantic/Faeroe": "Atlantic/Faroe",
        "Australia/ACT": "Australia/Sydney",
        "Australia/LHI": "Australia/Lord_Howe",
        "Australia/North": "Australia/Darwin",
        "Australia/NSW": "Australia/Sydney",
        "Australia/Queensland": "Australia/Brisbane",
        "Australia/South": "Australia/Adelaide",
        "Australia/Tasmania": "Australia/Hobart",
        "Australia/Victoria": "Australia/Melbourne",
        "Australia/West": "Australia/Perth",
        "Brazil/Acre": "America/Rio_Branco",
        "Brazil/DeNoronha": "America/Noronha",
        "Brazil/East": "America/Sao_Paulo",
        "Brazil/West": "America/Manaus",
        "Canada/Atlantic": "America/Halifax",
        "Canada/Central": "America/Winnipeg",
        "Canada/Eastern": "America/Toronto",
        "Canada/Mountain": "America/Edmonton",
        "Canada/Newfoundland": "America/St_Johns",
        "Canada/Pacific": "America/Vancouver",
        "Canada/Saskatchewan": "America/Regina",
        "Canada/Yukon": "America/Whitehorse",
        "Chile/Continental": "America/Santiago",
        "Chile/EasterIsland": "Pacific/Easter",
        "Cuba": "America/Havana",
        "Egypt": "Africa/Cairo",
        "Eire": "Europe/Dublin",
        "Europe/Kiev": "Europe/Kyiv",
        "Europe/Uzhgorod": "Europe/Kyiv",
        "Europe/Zaporozhye": "Europe/Kyiv",
        "GB": "Europe/London",
        "GB-Eire": "Europe/London",
        "GMT+0": "Etc/GMT",
        "GMT-0": "Etc/GMT",
        "GMT0": "Etc/GMT",
        "Greenwich": "Etc/GMT",
        "Hongkong": "Asia/Hong_Kong",
        "Iceland": "Africa/Abidjan",
        "Iran": "Asia/Tehran",
        "Israel": "Asia/Jerusalem",
        "Jamaica": "America/Jamaica",
        "Japan": "Asia/Tokyo",
        "Kwajalein": "Pacific/Kwajalein",
        "Libya": "Africa/Tripoli",
        "Mexico/BajaNorte": "America/Tijuana",
        "Mexico/BajaSur": "America/Mazatlan",
        "Mexico/General": "America/Mexico_City",
        "Navajo": "America/Denver",
        "NZ": "Pacific/Auckland",
        "NZ-CHAT": "Pacific/Chatham",
        "Pacific/Enderbury": "Pacific/Kanton",
        "Pacific/Ponape": "Pacific/Guadalcanal",
        "Pacific/Truk": "Pacific/Port_Moresby",
        "Poland": "Europe/Warsaw",
        "Portugal": "Europe/Lisbon",
        "PRC": "Asia/Shanghai",
        "ROC": "Asia/Taipei",
        "ROK": "Asia/Seoul",
        "Singapore": "Asia/Singapore",
        "Türkiye": "Europe/Istanbul",
        "UCT": "Etc/UTC",
        "Universal": "Etc/UTC",
        "US/Alaska": "America/Anchorage",
        "US/Aleutian": "America/Adak",
        "US/Arizona": "America/Phoenix",
        "US/Central": "America/Chicago",
        "US/Eastern": "America/New_York",
        "US/East-Indiana": "America/Indiana/Indianapolis",
        "US/Hawaii": "Pacific/Honolulu",
        "US/Indiana-Starke": "America/Indiana/Knox",
        "US/Michigan": "America/Detroit",
        "US/Mountain": "America/Denver",
        "US/Pacific": "America/Los_Angeles",
        "US/Samoa": "Pacific/Pago_Pago",
        "W-SU": "Europe/Moscow",
        "Zulu": "Etc/UTC",
    }


def _tz_mapping():
    return _TZ_MAPPING


# Computed lazily once and cached - the source data never changes at runtime.
_TZ_SELECTION = None


def _tz_get():
    """
        Get a list of timezones.
        :param self: Model instance.
        :return: list: List of timezones.
        """
    global _TZ_SELECTION
    if _TZ_SELECTION is None:
        # Start with all valid pytz timezones
        valid_timezones = set(pytz.all_timezones)
        filtered_timezones = valid_timezones - set(_TZ_MAPPING.keys())
        mapped_timezones = {new_tz for new_tz in _TZ_MAPPING.values() if
                            new_tz in valid_timezones}
        all_zones = filtered_timezones.union(mapped_timezones)
        _TZ_SELECTION = [(tz, tz) for tz in sorted(
            all_zones,
            key=lambda tz: tz if not tz.startswith('Etc/') else '_')]
    return _TZ_SELECTION


class ResUsers(models.Model):
    """
        Model for extending user details.
    """
    _inherit = 'res.users'

    banner_image = fields.Binary("Banner Image")

    @classmethod
    def _login(cls, db, login, password, user_agent_env):
        if not password:
            raise AccessDenied()
        ip = request.httprequest.environ['REMOTE_ADDR'] if request else 'n/a'
        try:
            with cls.pool.cursor() as cr:
                self = api.Environment(cr, SUPERUSER_ID, {})[cls._name]
                with self._assert_can_auth(user=login):
                    user = self.search(self._get_login_domain(login), order=self._get_login_order(), limit=1)
                    if not user:
                        raise AccessDenied()
                    user = user.with_user(user)
                    user._check_credentials(password, user_agent_env)
                    tz = request.httprequest.cookies.get('tz') if request else None
                    tz = _tz_mapping().get(tz, tz)
                    if not user.tz or not user.login_date:
                        # first login or missing tz -> set tz to browser tz
                        user.tz = tz
                    user._update_last_login()
        except AccessDenied:
            _logger.info("Login failed for db:%s login:%s from %s", db, login, ip)
            raise

        _logger.info("Login successful for db:%s login:%s from %s", db, login, ip)

        return user.id

    idle_timer = fields.Boolean(help="Enable idle timer to set idle time")
    idle_time = fields.Integer(string="Idle Time (In minutes)", default=10,
                               help="Set idle time for user. You will be logged out from the session"
                                    " once the timer ends")
    api_key = fields.Char(help="API key from OpenWeatherMap")
    location_set = fields.Selection(
        selection=[('auto', 'Use Browser Location'),
                   ('manual', 'Manual Location')],
        string="Set Location", default='auto',
        help="Use Browser Location: Fetching data based on browsers location, Manual Location:Need to specify the city"
             " in the city field")
    city = fields.Char()

    # SQL constraints
    _sql_constraints = [
        ('positive_idle_time', 'CHECK(idle_time >= 1)',
         'Idle Time should be a greater than or equal to one minute.'),
    ]

    @api.model
    def _check_credentials(self, password, user_agent_env):
        """
            Check user credentials and log login details.
        """
        res = super(ResUsers, self)._check_credentials(password, user_agent_env)
        try:
            current_tz = _tz_mapping()[
                self.env.user.tz] if self.env.user.tz in _tz_mapping() else self.env.user.tz
            login_time = fields.Datetime.now().astimezone(
                pytz.timezone(current_tz))
            ip_address = user_agent_env.get('REMOTE_ADDR')
            vals = {
                'name': self.name,
                'ip_address': ip_address,
                'date_time': login_time,
                'res_user_id': self.id,
            }
            self.env['login.user.detail'].sudo().create(vals)
        except Exception:
            return res
        return res

    @api.model
    def get_current_user_details(self):
        """
         Retrieves details of currently logged-in users
        """
        current_user = self.env.user
        return {
            'id': current_user.id,
            'name': current_user.name,
            'language': self.env['res.lang'].search(
                [('code', '=', current_user.lang)]).id,
            'active_lang': [
                {'id': lang.id, 'name': lang.name, 'code': lang.code}
                for lang in
                self.env['res.lang'].search([('active', '=', True)])],
            'work_email': current_user.email,
            'timezone': _tz_get(),
            'current_tz': _tz_mapping()[
                current_user.tz] if current_user.tz in _tz_mapping() else current_user.tz,
            'notif_type': current_user.notification_type,
        }

    @api.model
    def get_non_admin_user_details(self, user_id):
        """
         Retrieves details of currently logged in non-admin user
        """
        current_user = self.env.user
        allowed_companies = current_user.company_ids.read(
            ['id', 'name', 'email', 'phone', 'currency_id', 'parent_id', 'vat',
             'street', 'street2', 'state_id', 'country_id', 'zip'])
        return {
            'signature': current_user.signature,
            'groups_id': current_user.groups_id.ids,
            'model_access': current_user.groups_id.model_access.ids,
            'rule_groups': current_user.groups_id.rule_groups.ids,
            'action_id': current_user.action_id.name,
            'phone': current_user.partner_id.phone,
            'country': current_user.partner_id.country_id.name,
            'state': current_user.partner_id.state_id.name,
            'street': current_user.partner_id.street,
            'street2': current_user.partner_id.street2,
            'zip': current_user.partner_id.zip,
            'allowed_companies': allowed_companies,
            'job_position': current_user.employee_id.job_id.name
            if hasattr(current_user,
                       'employee_id') and current_user.employee_id else False,
            'default_company': {'id': current_user.company_id.id,
                                'name': current_user.company_id.name},
        }

    @api.model
    def get_change_pwd_view_id(self):
        """
            Retrieve the ID of the 'Change Password' dashboard form view.
        """
        return self.env.ref('cyllo_dashboard.view_change_password_own_form').id

    @api.model
    def get_groups(self):
        """
            Retrieve the IDs of the groups associated with the current user.
        """
        return self.env.user.groups_id.ids

    @api.model
    def toggle_auto_edit(self, auto_edit):
        self.env.user.sudo().write({
            'auto_edit': auto_edit
        })

    @api.model
    def get_auto_edit_value(self):
        return self.env.user.auto_edit


class ChangePasswordOwn(models.TransientModel):
    """
        Model for changing own password.
    """
    _inherit = "change.password.own"

    old_password = fields.Char(string="Old Password")

    def action_change_password_dashboard(self):
        """
            Change password through dashboard.
            :return: dict: Action to reload.
        """
        user = self.env.user

        try:
            user._check_credentials(self.old_password,user_agent_env=None)
        except AccessDenied:
            raise ValidationError("Old password is incorrect.")
        self.env.user._change_password(self.new_password)
        self.unlink()
        return {'type': 'ir.actions.client', 'tag': 'reload'}
