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
from odoo import api, fields, models


class OnboardingIndustry(models.Model):
    """
    Represents a curated industry vertical used during the onboarding flow.
    Each record stores the vertical's display name, a RemixIcon CSS class,
    the linked base partner industry, and the recommended Odoo module names.
    """
    _name = 'onboarding.industry'
    _description = 'Onboarding Industry Vertical'
    _order = 'sequence, name'

    name = fields.Char(
        string='Name',
        required=True,
        translate=True,
        help='Display name of the industry vertical shown on the onboarding grid.',
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Determines the display order in the onboarding industry grid.',
    )
    icon = fields.Char(
        string='Icon Class',
        required=True,
        help='RemixIcon CSS class used to render the industry card icon, e.g. ri-computer-line.',
    )
    base_industry_id = fields.Many2one(
        comodel_name='res.partner.industry',
        string='Base Industry',
        ondelete='set null',
        help='Maps this vertical to a standard partner industry category.',
    )
    app_names = fields.Char(
        string='Recommended App Names',
        help='Comma-separated list of ir.module.module technical names to suggest for this vertical.',
    )

    @api.model
    def get_industry_verticals(self):
        """
        Return all industry verticals as a list of dicts, each containing:
          id, name, icon, base_industry (name string), and apps (list of module names).
        This method is called from the frontend onboarding component.
        """
        records = self.sudo().search_read(
            [],
            ['name', 'icon', 'base_industry_id', 'app_names'],
            order='sequence, name',
        )
        result = []
        for rec in records:
            apps = [m.strip() for m in (rec['app_names'] or '').split(',') if m.strip()]
            result.append({
                'id': rec['id'],
                'name': rec['name'],
                'icon': rec['icon'],
                'base_industry': rec['base_industry_id'][1] if rec['base_industry_id'] else '',
                'apps': apps,
            })
        return result
