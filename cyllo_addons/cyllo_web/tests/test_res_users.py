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
import logging

from odoo.addons.cyllo_web.models.res_users import _get_time, _get_schedule_date

from odoo import fields
from odoo.tests import common
from odoo.tools.safe_eval import pytz

_LOGGER = logging.getLogger(__name__)


class TestResUsers(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.users = cls.env['res.users'].create({'name': 'Tim Cook', 'login': 'tim@gmail.com',
                                                 'is_dark_mode': False, 'start_time': '11 : 30 PM',
                                                 'end_time': '7 : 24 AM', 'tz': 'Asia/Calcutta'})
        cls.users._check_start_time()
        cls.time = _get_time(cls.users.start_time).split(':')[0] + ":" + _get_time(cls.users.start_time).split(':')[1] + ":00"
        cls.key = 'start_time'
        cls.condition = True

    def test_for_fields(self):
        """Test for the fields in 'res users'"""
        _LOGGER.info("Starts tests for 'res users'")

        cron_start = self.env.ref('cyllo_web.ir_cron_darkmode_schedule_dark_mode_enable').id
        cron_end = self.env.ref('cyllo_web.ir_cron_darkmode_schedule_dark_mode_disable').id
        trigger_start_id = self.env['ir.cron.trigger'].create({'cron_id': cron_start})
        trigger_end_id = self.env['ir.cron.trigger'].create({'cron_id': cron_end})
        self.users.update({'dark_mode_selection': 'scheduled',
                           'ir_cron_trigger_start_id': trigger_start_id.id,
                           'ir_cron_trigger_end_id': trigger_end_id.id})
        self.assertEqual(self.users.name, 'Tim Cook')
        self.assertEqual(self.users.login, 'tim@gmail.com')
        self.assertEqual(self.users.is_dark_mode, False)
        self.assertEqual(self.users.dark_mode_selection, 'scheduled')
        self.assertEqual(self.users.start_time, '11 : 30 PM')
        self.assertEqual(self.users.end_time, '7 : 24 AM')
        self.assertEqual(self.users.ir_cron_trigger_start_id, trigger_start_id)
        self.assertEqual(self.users.ir_cron_trigger_end_id, trigger_end_id)

        _LOGGER.info("End 'res users' fields test")

    def test_get_active(self):
        """Test for the get_active function"""
        _LOGGER.info("Begins Tests for 'get_active'")

        active_result = self.users.get_active()
        self.assertEqual(self.users.is_dark_mode, active_result)

        _LOGGER.info("End of get_active tests")

    def test_toggle_night_mode(self):
        """Test for the toggle_night_mode function"""
        _LOGGER.info("Begins Tests for 'toggle_night_mode'")

        result = self.users.toggle_night_mode(self.users.is_dark_mode)
        self.assertEqual(self.users.is_dark_mode, result)

        _LOGGER.info("Test toggle_night_mode end")

    def test_validate_dark_mode_scheduler(self):
        """Test for the _check_start_time function"""
        _LOGGER.info("Begins Tests for '_check_start_time'")
        self.users._check_start_time()
        _LOGGER.info("Test _check_start_time end")

    def test_create_ir_cron_trigger(self):
        """Test for the _create_ir_cron_trigger function"""
        _LOGGER.info("Begins test for '_create_ir_cron_trigger'")
        self.users._create_ir_cron_trigger(self.condition, self.key, self.time)
        date_time = _get_schedule_date(self.condition, self.time)
        _LOGGER.info("Test _create_ir_cron_trigger end")
        return self.key, date_time

    def test_schedule_time_trigger(self):
        """Test for the _schedule_time_trigger function"""
        _LOGGER.info("Begins test for '_schedule_time_trigger'")

        result_key, date_time = self.test_create_ir_cron_trigger()
        self.users._schedule_time_trigger(result_key, date_time)
        if result_key == 'start_time':
            self.assertEqual(self.users.ir_cron_trigger_start_id.cron_id.id, self.env.ref(
                'cyllo_web.ir_cron_darkmode_schedule_dark_mode_enable').id)
        else:
            self.assertEqual(self.users.ir_cron_trigger_end_id.cron_id.id, self.env.ref(
                'cyllo_web.ir_cron_darkmode_schedule_dark_mode_disable').id)

        _LOGGER.info("Test _schedule_time_trigger end")

    def test_get_date_obj_next(self):
        """Test for the _get_date_obj_next function"""
        _LOGGER.info("Starts test for '_get_date_obj_next'")
        # Ensure we are using a consistent time string
        test_time_str = '11 : 30 PM'
        time = _get_time(test_time_str)
        date_obj = self.users._get_date_obj_next(time)
        # Calculate expected UTC time for comparison
        local_tz = pytz.timezone(self.users.tz or 'GMT')
        local_date_obj = fields.datetime.strptime(f'{str(fields.date.today())} {time}', "%Y-%m-%d %H:%M:%S")
        local_dt = local_tz.localize(local_date_obj, is_dst=None)
        utc_dt = local_dt.astimezone(pytz.utc)
        expected_utc = fields.Datetime.to_string(utc_dt)
        self.assertEqual(date_obj, expected_utc)
        _LOGGER.info("End test for '_get_date_obj_next'")

    def test_schedule_dark_mode_enable(self):
        """Test for the schedule_dark_mode_enable function"""
        _LOGGER.info("Starts test for 'schedule_dark_mode_enable'")
        self.users.schedule_dark_mode_enable()
        _LOGGER.info("End test for 'schedule_dark_mode_enable'")

    def test_schedule_dark_mode_disable(self):
        """Test for the schedule_dark_mode_disable function"""
        _LOGGER.info("Starts test for 'schedule_dark_mode_disable'")
        self.users.schedule_dark_mode_disable()
        _LOGGER.info("End test for 'schedule_dark_mode_disable'")

    def test_get_system_time(self):
        """Test for the _get_system_time function"""
        _LOGGER.info("Starts test for '_get_system_time'")
        formatted_date = fields.datetime.strftime(fields.datetime.now(pytz.utc).astimezone(
            pytz.timezone(self.users.tz)), "%H:%M:00")
        result = self.users._get_system_time()
        self.assertEqual(result, formatted_date)
        _LOGGER.info("End test for '_get_system_time'")
