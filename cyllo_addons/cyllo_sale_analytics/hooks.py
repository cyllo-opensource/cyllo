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
import os
import resource

import psutil

from odoo.exceptions import UserError
from odoo.tools import config

REQUIRED_LIMITS = [
    ('limit_memory_soft', 8589934592, '~8 GiB'),
    ('limit_memory_hard', 10737418240, '~10 GiB'),
    ('limit_time_cpu', 1200, '20 minutes'),
    ('limit_time_real', 2400, '40 minutes'),
]
REQUIRED_SYSTEM_MEMORY = 10737418240


def _gib(value):
    """Format a byte count as GiB for the error message."""
    return "%.1f GiB" % (value / 1024 ** 3)


def _cgroup_memory_limit():
    """Return the container (cgroup) memory limit in bytes, or None if unlimited."""
    paths = []
    try:
        with open('/proc/self/cgroup') as cgroup_file:
            for line in cgroup_file:
                hierarchy, controllers, path = line.strip().split(':', 2)
                if hierarchy == '0':
                    paths.append('/sys/fs/cgroup%s/memory.max' % path.rstrip('/'))
                elif 'memory' in controllers.split(','):
                    paths.append('/sys/fs/cgroup/memory%s/memory.limit_in_bytes' % path.rstrip('/'))
    except (OSError, ValueError):
        pass
    paths += ['/sys/fs/cgroup/memory.max', '/sys/fs/cgroup/memory/memory.limit_in_bytes']
    for path in paths:
        if os.path.exists(path):
            with open(path) as limit_file:
                value = limit_file.read().strip()
            if value.isdigit() and int(value) < psutil.virtual_memory().total:
                return int(value)
            return None
    return None


def check_system_capacity():
    """Return the OS memory problems that keep the required limits from being usable."""
    problems = []
    total = psutil.virtual_memory().total
    if total < REQUIRED_SYSTEM_MEMORY:
        problems.append("Server RAM is %s, at least %s is required. Add memory to this machine."
                        % (_gib(total), _gib(REQUIRED_SYSTEM_MEMORY)))
    cgroup_limit = _cgroup_memory_limit()
    if cgroup_limit is not None and cgroup_limit < REQUIRED_SYSTEM_MEMORY:
        problems.append("The container memory limit is %s, at least %s is required. "
                        "Raise the memory limit of the container."
                        % (_gib(cgroup_limit), _gib(REQUIRED_SYSTEM_MEMORY)))
    hard_as = resource.getrlimit(resource.RLIMIT_AS)[1]
    if hard_as != resource.RLIM_INFINITY and hard_as < REQUIRED_SYSTEM_MEMORY:
        problems.append("The OS address-space limit (ulimit -v) is %s, at least %s is required. "
                        "Raise it for the user running the server."
                        % (_gib(hard_as), _gib(REQUIRED_SYSTEM_MEMORY)))
    return problems


def check_server_limits():
    """Stop with the required odoo.conf values when a server limit is too low.

    A value of 0 or less means the limit is disabled, so it is accepted.
    """
    too_low = []
    for key, required, label in REQUIRED_LIMITS:
        current = int(config.get(key) or 0)
        if 0 < current < required:
            too_low.append("%s = %s    (current: %s, required: at least %s, %s)"
                           % (key, required, current, required, label))
    if too_low:
        raise UserError(
            "Cyllo Sale Analytics cannot be installed: the server limits in "
            "odoo.conf are too low for the prediction models.\n\n"
            "Change these lines in odoo.conf, restart the server and install "
            "the module again:\n\n%s" % "\n".join(too_low))


def pre_init_hook(env):
    """Refuse to install while the OS capacity or the server limits are below the requirement."""
    problems = check_system_capacity()
    if problems:
        raise UserError(
            "Cyllo Sale Analytics cannot be installed: this server does not have "
            "enough memory for the prediction models.\n\n%s" % "\n".join(problems))
    check_server_limits()
