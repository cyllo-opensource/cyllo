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
import calendar
from datetime import datetime

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

MONTH_SELECTION = [('1', 'January'), ('2', 'February'), ('3', 'March'),
                   ('4', 'April'), ('5', 'May'), ('6', 'June'),
                   ('7', 'July'), ('8', 'August'), ('9', 'September'),
                   ('10', 'October'), ('11', 'November'),
                   ('12', 'December')]


class ResConfigSettings(models.TransientModel):
    """ Inherited res.config.settings to add api keys"""
    _inherit = 'res.config.settings'

    openai_api_key = fields.Char(
        config_parameter='cyllo_analytics.openai_api_key')
    # A "module_<name>" boolean: ticking it installs cyllo_ai_analytics,
    # unticking it uninstalls it (standard Odoo settings machinery — no custom
    # code needed). It brings the AI assistant's analytics features into the
    # dashboards; the assistant also needs an LLM configured in Cyllo AI settings.
    module_cyllo_ai_analytics = fields.Boolean(
        string="AI Analytics Assistant",
        help="Enable AI-powered analytics (chart recommendation and more) via "
             "the Cyllo AI assistant. Installs the Cyllo AI Analytics module. "
             "Requires an LLM configured under Cyllo AI settings to function.")
    is_financial_year = fields.Boolean(
        string='Predict Churn based on Financial Year',
        config_parameter='cyllo_analytics.is_financial_year'
    )
    fiscal_year_last_month = fields.Selection(
        MONTH_SELECTION,
        default='3',
        string='Month',
        config_parameter='cyllo_analytics.fiscal_year_last_month'
    )
    fiscal_year_last_day = fields.Integer(
        config_parameter='cyllo_analytics.fiscal_year_last_day',
        default=31
    )
    limit_record = fields.Boolean(
        string='Limit Records',
        config_parameter='cyllo_analytics.limit_record'
    )
    limit = fields.Integer(
        default=1000,
        config_parameter='cyllo_analytics.limit'
    )

    @api.constrains('fiscal_year_last_day', 'fiscal_year_last_month')
    def _check_fiscal_year_last_day(self):
        """Check if the fiscal year last day is valid based on the selected month."""
        for rec in self:
            max_day = calendar.monthrange(datetime.now().year,
                                          int(rec.fiscal_year_last_month))[1]
            if rec.fiscal_year_last_day > max_day:
                raise ValidationError(_("Invalid fiscal year last day"))
