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
from odoo import tools, fields, models


class AssetReport(models.Model):
    _name = "asset.report"
    _description = "Asset Activity Analysis"
    _auto = False
    _rec_name = "asset_id"

    asset_id = fields.Many2one('asset.asset', string="Asset", readonly=True)
    activity_type = fields.Selection([
        ('maintenance', 'Maintenance'),
        ('lease', 'Lease'),
        ('rent', 'Rental'),], string="Activity Type", readonly=True)
    activity_count = fields.Integer(string="Activity Count", readonly=True)
    company_id = fields.Many2one(
        'res.company',
        string="Company",
        readonly=True,
    )

    def init(self):
        """Drop the existing SQL view (if any) and recreate it for the asset activity report."""
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    row_number() OVER() AS id,
                    a.id AS asset_id,
                     a.company_id AS company_id,
                    'lease' AS activity_type,
                    COUNT(l.id) AS activity_count
                FROM asset_asset a
                LEFT JOIN asset_lease l
                    ON l.asset_id = a.id
                GROUP BY a.id
                UNION ALL
                SELECT
                    row_number() OVER() + 10000 AS id,
                    a.id AS asset_id,
                     a.company_id AS company_id,
                    'rent' AS activity_type,
                    COUNT(r.id) AS activity_count
                FROM asset_asset a
                LEFT JOIN asset_rental r
                    ON r.asset_id = a.id
                GROUP BY a.id
                UNION ALL
                SELECT
                    row_number() OVER() + 20000 AS id,
                    a.id AS asset_id,
                     a.company_id AS company_id,
                    'maintenance' AS activity_type,
                    COUNT(m.id) AS activity_count
                FROM asset_asset a
                LEFT JOIN maintenance_request m
                    ON m.asset_id = a.id
                GROUP BY a.id
            )""" % self._table)