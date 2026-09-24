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
def _pre_init_cyllo_timesheet_grid(env):
    env.cr.execute("""INSERT INTO ir_config_parameter (key, value)
                      VALUES ('cyllo_timesheet_grid.minimal_duration', '15');""")
    env.cr.execute("""INSERT INTO ir_config_parameter (key, value)
                        VALUES ('cyllo_timesheet_grid.round_up', '15');""")


def _uninstall_hook_cyllo_timesheet_grid(env):
    env.cr.execute(
        """DELETE FROM ir_config_parameter WHERE key 
        = 'cyllo_timesheet_grid.minimal_duration'""")
    env.cr.execute(
        """DELETE FROM ir_config_parameter WHERE key
         = 'cyllo_timesheet_grid.round_up'""")
    timesheet_action_all = env.ref('hr_timesheet.timesheet_action_all')
    timesheet_action = env.ref('hr_timesheet.act_hr_timesheet_line')
    timesheet_action_all.write({'view_mode': 'tree,form,kanban,pivot,graph'})
    timesheet_action.write({'view_mode': 'tree,form,kanban,pivot,graph'})
