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
import platform
import psutil

from odoo.http import Controller, request, route
from odoo.tools import config


class PerformanceController(Controller):
    """Controller for managing system performance data."""

    @route('/performance/memory', methods=['POST'], type='json', auth='user',
           csrf=False)
    def get_memory_performance(self):
        """Lightweight, non-blocking memory & disk stats.

        Feeds the dashboard 'Memory' chart for every user without running any
        of the heavy/blocking system profiling done by ``/performance``.
        """
        storage = psutil.virtual_memory()
        total_ram = round(storage.total / (1024.0 ** 3), 2)
        hdd = psutil.disk_usage('/')
        used_memory = round(hdd.used / 1000000000, 2)
        free_memory = round(hdd.free / 1000000000, 2)
        return {
            'ram_percent': storage.percent,
            'total_ram': total_ram,
            'used_memory': used_memory,
            'total_memory': round(used_memory + free_memory, 2),
        }

    @route('/performance', methods=['POST'], type='json', auth='user',
           csrf=False)
    def get_performance(self):
        """Admin-only system & Odoo configuration insight.

        Only the values actually rendered by the dashboard are computed. CPU
        usage uses a short, non-blocking sample instead of a multi-second
        blocking one, and no per-process scanning is performed.
        """
        if not request.env.is_admin():
            return {'is_admin': False}
        os_dict = {
            'operating_system': platform.system(),
        }
        conf_dict = {
            'db_user': config.get('db_user'),
            'transient_age_limit': config.get('transient_age_limit'),
            'limit_memory_hard': round(
                (config.get('limit_memory_hard') / 1000000000), 2),
            'limit_memory_soft': round(
                (config.get('limit_memory_soft') / 1000000000), 2),
            'limit_request': config.get('limit_request'),
            'limit_time_cpu': config.get('limit_time_cpu'),
            'limit_time_real': config.get('limit_time_real'),
            'max_cron_threads': config.get('max_cron_threads'),
            'workers': config.get('workers'),
            'http_port': config.get('http_port'),
        }
        return {
            'is_admin': True,
            'total_cpu_usage': psutil.cpu_percent(interval=0.1),
            'os_dict': os_dict,
            'conf_dict': conf_dict,
        }
