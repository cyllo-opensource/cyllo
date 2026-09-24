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
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import pytz


def _is_first_time_greater(time_str1, time_str2):
    """
        Compare two time strings in "HH:MM:SS" format and check if the first
        time is greater than the second.
        Args:
            time_str1 (str): The first time string to compare.
            time_str2 (str): The second time string to compare.
        Returns:
            bool: True if the first time is greater than the second; False
            otherwise.
    """
    try:
        # Parse the time strings into datetime objects
        time1 = fields.datetime.strptime(str(time_str1), "%H:%M:%S")
        time2 = fields.datetime.strptime(str(time_str2), "%H:%M:%S")
        # Compare the datetime objects
        return time1 > time2
    except ValueError:
        # Handle parsing errors (e.g., invalid time format)
        return False


def _get_time(time_str):
    """
        Convert a time string from a custom format to the "HH:MM:SS" format.
        Args:
            time_str (str): The input time string in a custom format, e.g.,
            "11 : 30 AM".
        Returns:
            str: The time string converted to the "HH:MM:SS" format, e.g.,
            "11:30:00"."""
    # Split the input time string into hours, minutes, and AM/PM parts
    hours_minutes = time_str.split(' : ')
    hours = int(hours_minutes[0])
    minute, am_pm = hours_minutes[1].split(' ')
    # Convert AM/PM format to 24-hour format
    if am_pm == "AM":
        hours = 0 if hours == 12 else hours
    else:  # PM
        if hours != 12:
            hours += 12
    # Format the time as "HH:MM:SS"
    modified_time_str = f"{hours:02d}:{minute}:00"
    return modified_time_str


def _get_schedule_date(condition, time):
    """
        Get a schedule date based on a condition and time.
        Args:
            condition (bool): A condition that determines whether the date
            should be today or tomorrow.
            time (str): The time in "HH:MM:SS" format.
        Returns:
            datetime: A datetime object representing the scheduled date and
            time.
    """
    # Determine whether to use today or tomorrow based on the condition
    val = 0 if condition else 1
    # Create a datetime object combining the date (today or tomorrow)
    # and the provided time
    return fields.Datetime.from_string(f'{str(fields.Date.today() + relativedelta(days=val))} {time}')


class ResUsers(models.Model):
    """ Inherit res users """
    _inherit = "res.users"

    is_dark_mode = fields.Boolean(string="Night Mode", default=False, help="Enable / Disable checkbox")
    dark_mode_selection = fields.Selection([('none', 'None'), ('scheduled', 'Turn on at custom time')],
                                           help='Choose the options to choose whether schedule dark mode or not to '
                                                'schedule dark mode', default='none')
    start_time = fields.Char(string='From', help="Set the time to schedule(enable) dark mode.")
    end_time = fields.Char(string='To', help="Set the time to schedule(disable) dark mode.")
    ir_cron_trigger_start_id = fields.Many2one('ir.cron.trigger', string='Cron Trigger Enable Relation',
                                               help='Scheduled action trigger time for enable dark mode')
    ir_cron_trigger_end_id = fields.Many2one('ir.cron.trigger', string='Cron Trigger Disable Relation',
                                             help='Scheduled action trigger time for disable dark mode')

    systray_pins = fields.Json("Systray pins",
                               default=["mail.activity_menu", "mail.messaging_menu"])

    @api.constrains('dark_mode_selection', 'start_time', 'end_time')
    def _check_dark_mode_selection(self):
        """
            Constraint method to check if scheduled dark mode is selected and
            start/end times are provided.
            This method is used to enforce a constraint where, if the user
            selects the 'scheduled' dark mode, both the start time and
            end time must be provided.
            Raises:
                ValidationError: If 'scheduled' dark mode is selected but
                either start time or end time is missing.
            Note:
                This constraint ensures that valid scheduling information
                is provided when scheduling dark mode.
        """
        if self.env.user.dark_mode_selection == 'scheduled':
            if not self.env.user.start_time or not self.env.user.end_time:
                raise ValidationError(_("Please Choose the Schedule Time"))

    @api.model
    def get_active(self):
        """ Get value of field is_dark_mode.
            :param : model
            :return :  value of is_dark_mode"""
        return self.env.user.is_dark_mode

    @api.model
    def toggle_night_mode(self, toggle_value):
        """
            Toggle night mode for the current user.
            :param toggle_value: Boolean value indicating whether to enable or
            disable night mode.
            :type toggle_value: bool
            :return: The updated value of night mode toggle.
            :rtype: bool"""
        self.env.user.sudo().is_dark_mode = toggle_value
        return self.env.user.is_dark_mode

    @api.constrains('start_time', 'end_time')
    def _check_start_time(self):
        """
            Validate the dark mode scheduler times and create cron triggers.
            This method is used to validate the start and end times for the
            dark mode scheduler. It also creates
            cron triggers based on the provided times and conditions.
            Args:
                self: The current recordset.
            Note:
                - The method compares the start and end times with the system
                time.
                - If the start time is greater than the system time, it
                schedules dark mode enablement.
                - If the end time is less than the system time, it schedules
                dark mode disablement.
                - Cron triggers are created accordingly based on the
                conditions.
        """
        system_time = self._get_system_time()
        for key, val in {'start_time': self.start_time, 'end_time': self.end_time}.items():
            # Checks whether the first time is greater than the second time.
            if val:
                time = _get_time(val)
                condition = _is_first_time_greater(time, system_time)
                time = self._get_date_obj_next(time).split(' ')[1]
                self._create_ir_cron_trigger(condition, key, time)

    def _create_ir_cron_trigger(self, condition, key, time):
        """
           Create or update an IR Cron Trigger based on a condition and time.
           This method is used to create or update an IR Cron Trigger based on
           the provided condition and time.
           It can be used for scheduling dark mode enablement or disablement.
           Args:
               condition (bool): A condition that determines whether the action
                    should be scheduled.
               key (str): A key indicating whether it's the start or end time
                    ('start_time' or 'end_time').
               time (str): The time in "HH:MM:SS" format to schedule the
                    action.
           Note:
               - If the key is 'start_time' and the condition is met, it
                    schedules dark mode enablement.
               - If the key is 'end_time' and the condition is met, it
                    schedules dark mode disablement.
               - The existing IR Cron Trigger is unlinked and a new one is
                    created based on the provided time.
       """
        # Unlink the existing IR Cron Trigger based on the key
        self.ir_cron_trigger_start_id.unlink() if key == 'start_time' else self.ir_cron_trigger_end_id.unlink()
        # Calculate the scheduled date and time
        date_time = _get_schedule_date(condition, time)
        # Schedule the action using a new IR Cron Trigger
        self._schedule_time_trigger(key, date_time)

    def _schedule_time_trigger(self, key, time):
        """
            Schedule an IR Cron Trigger based on a key and time.
            This method is used to schedule an IR Cron Trigger based on the
            provided key ('start_time' or 'end_time')
            and the specified time.
            Args:
                key (str): A key indicating whether it's the start or end time
                    ('start_time' or 'end_time').
                time (datetime): The datetime object representing the scheduled
                    date and time.
            Note:
                - If the key is 'start_time', it creates an IR Cron Trigger
                    for enabling dark mode.
                - If the key is 'end_time', it creates an IR Cron Trigger for
                    disabling dark mode.
                - The created IR Cron Trigger is associated with the specified
                    time.
        """
        if key == 'start_time':
            # Get the cron ID for enabling dark mode
            cron_id = self.env.ref('cyllo_web.ir_cron_darkmode_schedule_dark_mode_enable')
            # Create a new IR Cron Trigger for enabling dark mode
            trigger = self.ir_cron_trigger_start_id.create({
                'cron_id': cron_id.id,
                'call_at': time
            })
            # Update the reference to the IR Cron Trigger
            self.ir_cron_trigger_start_id = trigger.id
        else:
            # Get the cron ID for disabling dark mode
            cron_id = self.env.ref('cyllo_web.ir_cron_darkmode_schedule_dark_mode_disable')
            # Create a new IR Cron Trigger for disabling dark mode
            trigger = self.ir_cron_trigger_end_id.create({
                'cron_id': cron_id.id,
                'call_at': time
            })
            # Update the reference to the IR Cron Trigger
            self.ir_cron_trigger_end_id = trigger.id

    def _get_date_obj_next(self, time):
        """
            Get a datetime object representing the next occurrence of a
            specified time.
            This method takes a time in "HH:MM:SS" format and calculates the
            next occurrence of that time based on the current date and the
            timezone set for the user.
            Args:
                self: The current recordset.
                time (str): The time in "HH:MM:SS" format for which to
                    calculate the next occurrence.
            Returns:
                str: A string representing the datetime of the next occurrence
                    in "YYYY-MM-DD HH:MM:SS" format.
        """
        # Create a datetime object using the current date and the provided time
        date_obj = fields.Datetime.from_string(f'{str(fields.Date.today())} {time}')
        # Get the local timezone, defaulting to GMT if not specified
        local_tz = pytz.timezone(self.tz or 'GMT')
        # Localize the datetime object using the user's timezone
        local_dt = local_tz.localize(date_obj, is_dst=None)
        # Convert the localized datetime to UTC timezone
        utc_dt = local_dt.astimezone(pytz.utc)
        # Format the UTC datetime as a string in "YYYY-MM-DD HH:MM:SS" format
        utc_dt = utc_dt.strftime("%Y-%m-%d %H:%M:%S")
        # Parse the formatted string back into a datetime object
        date_obj = fields.datetime.strptime(utc_dt, "%Y-%m-%d %H:%M:%S")
        # Convert the datetime object back to a string
        date_obj = fields.Datetime.to_string(date_obj)
        return date_obj

    def schedule_dark_mode_enable(self):
        """
            Schedule dark mode enablement for users with specified start times.
            This method is responsible for scheduling dark mode enablement for
                users who have specified start times.
            It calculates the next occurrence of the start time, creates an IR
                Cron Trigger for it, and sends a notification.
            Args:
                self: The current recordset.
            Note:
                - It retrieves users with specified start times.
                - It converts and compares times based on user timezones.
                - If the user's start time matches the current time, it
                    schedules dark mode enablement.
                - A notification is sent to the user for refreshing to activate
                    Dark Mode.
        """
        users = self.env['res.users'].search([('start_time', '!=', False)])
        current_time_utc = fields.datetime.now(pytz.utc)
        for user in users:
            if user.tz:
                system_timezone = pytz.timezone(user.tz)
                current_time_local = current_time_utc.astimezone(system_timezone)
                utc_dt = fields.datetime.strftime(current_time_local, "%H:%M:00")
                time = _get_time(user.start_time)
                date_obj = fields.Datetime.from_string(f'{str(fields.Date.today())} {time}')
                local_timezone = pytz.timezone(user.tz or 'GMT')
                local_date = local_timezone.localize(date_obj, is_dst=None)
                utc_date = local_date.astimezone(pytz.utc)
                utc_date = utc_date.strftime("%Y-%m-%d %H:%M:%S")
                date_obj = fields.datetime.strptime(utc_date, "%Y-%m-%d %H:%M:%S")
                time_part = date_obj.strftime("%H:%M")
                if _get_time(user.start_time) == str(utc_dt):
                    user.is_dark_mode = True
                    cron_id = self.env.ref('cyllo_web.ir_cron_darkmode_schedule_dark_mode_enable')
                    trigger = user.ir_cron_trigger_start_id.create({
                        'cron_id': cron_id.id,
                        'call_at': fields.Datetime.from_string(f"""{str(fields.Date.today() +
                                                                        relativedelta(days=1))} {time_part}""")
                    })
                    user.ir_cron_trigger_start_id = trigger.id
                    self.env['bus.bus']._sendone(user.partner_id, 'simple_notification',
                                                 {'title': _('Refresh Now'),
                                                  'message': _('Refresh Now To activate Dark Mode')})

    def schedule_dark_mode_disable(self):
        """
            Schedule dark mode disablement for users with specified end times.
            This method is responsible for scheduling dark mode disablement for
            users who have specified end times, based on their timezones.
            Args:
                self: The current recordset.
            Note:
                - It retrieves users with specified end times.
                - It converts and compares times based on user timezones.
                - If the user's end time matches the current time, it schedules
                    dark mode disablement.
                - A notification is sent to the user for refreshing to
                    deactivate Dark Mode.
        """
        users = self.env['res.users'].search([('end_time', '!=', False)])
        current_time_utc = fields.datetime.now(pytz.utc)
        for user in users:
            if user.tz:
                system_timezone = pytz.timezone(user.tz)
                current_time_local = current_time_utc.astimezone(system_timezone)
                utc_dt = fields.datetime.strftime(current_time_local, "%H:%M:00")
                time = _get_time(user.end_time)
                date_obj = fields.Datetime.from_string(f'{str(fields.Date.today())} {time}')
                local_timezone = pytz.timezone(user.tz or 'GMT')
                local_date = local_timezone.localize(date_obj, is_dst=None)
                utc_date = local_date.astimezone(pytz.utc)
                utc_date = utc_date.strftime("%Y-%m-%d %H:%M:%S")
                date_obj = fields.datetime.strptime(utc_date, "%Y-%m-%d %H:%M:%S")
                time_part = date_obj.strftime("%H:%M")
                if _get_time(user.end_time) == str(utc_dt):
                    user.is_dark_mode = False
                    cron_id = self.env.ref('cyllo_web.ir_cron_darkmode_schedule_dark_mode_disable')
                    trigger = user.ir_cron_trigger_end_id.create({
                        'cron_id': cron_id.id,
                        'call_at': fields.Datetime.from_string(f"""{str(fields.Date.today() +
                                                                        relativedelta(days=1))} {time_part}""")})
                    user.ir_cron_trigger_end_id = trigger.id
                    self.env['bus.bus']._sendone(user.partner_id, 'simple_notification',
                                                 {'title': _('Refresh Now'),
                                                  'message': _('Refresh Now To deactivate Dark Mode')})

    def _get_system_time(self, user=None):
        """
            Get the current system time in the specified user's timezone or the
            system's timezone.
            This method is used to retrieve the current system time in a
            specific user's timezone or in the system's timezone
            if no user is specified.
            Args:
                self: The current recordset.
                user (res.users): The user for whom to retrieve the time
                    (optional).
            Returns:
                str: A string representing the current time in "HH:MM:00"
                    format.
        """
        current_time_utc = fields.datetime.now(pytz.utc)
        val = user.tz if user else self.tz
        if val:
            system_timezone = pytz.timezone(val)
            current_time_local = current_time_utc.astimezone(system_timezone)
            return fields.datetime.strftime(current_time_local, "%H:%M:00")

    @property
    def SELF_WRITEABLE_FIELDS(self):
        """
            Get the list of fields that are writeable by the user.

            This property defines the list of fields that a user can write to.
            It extends the list of writeable fields provided by the superclass
            by adding custom fields related to dark mode settings and cron
            triggers.
            Returns:
                list: A list of field names that are writeable by the user.
        """
        return super().SELF_WRITEABLE_FIELDS + ['dark_mode_selection', 'start_time', 'end_time',
                                                'ir_cron_trigger_start_id', 'ir_cron_trigger_end_id']

    def pin_systray_icons(self, pins):
        """Writes the pinned systray for user"""
        self.sudo().write({"systray_pins": pins})
