# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cyllo(<https://www.cyllo.com>)
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
"""Shared field-level access constants for the raw-analytics read paths.

Raw SQL (dashboard charts, the ``analytic_record`` tool, AI chart proposals)
bypasses Odoo's field security, so the callers must re-apply it. Group-restricted
fields are enforced per field via each field's own ``groups`` (or, for
metadata-driven paths, by using ``fields_get()`` which already filters by group).
This module holds the one piece with no ``groups`` to lean on — the masked
credential columns — so every path denies the same set.
"""

# Columns never surfaced via raw analytics, whatever the model ACL says:
# credential/secret fields Odoo masks specially at the ORM layer and that carry
# no field ``groups`` to enforce.
SENSITIVE_COLUMNS = frozenset({
    'password', 'password_crypt', 'totp_secret', 'api_key',
})
