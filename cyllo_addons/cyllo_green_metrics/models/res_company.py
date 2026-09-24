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
from odoo import api, fields, models, _
from markupsafe import Markup

class ResCompany(models.Model):
    _inherit = 'res.company'

    carbon_cap = fields.Float(
        string='Carbon Cap',
        help='Maximum allowed carbon emissions'
    )
    previous_year_achieved = fields.Float(
        string='Previous Year Achieved',
        help='Carbon emissions achieved in the previous year'
    )
    targeted_achievement = fields.Float(
        string='Targeted Achievement',
        help='Targeted carbon emissions achievement'
    )
    carbon_unit = fields.Selection([
        ('kg', 'kg CO2e'),
        ('t', 't CO2e'),
    ], string='Unit', default='t')
    carbon_duration = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('half_yearly', '6 Months'),
        ('yearly', 'Yearly'),
    ], string='Duration', default='yearly')

    water_cap = fields.Float(
        string='Allocated Water',
        help='Maximum allowed water usage'
    )
    water_unit = fields.Selection([
        ('L', 'L'),
        ('KL', 'KL'),
        ('tonnes', 'tonnes'),
    ], string='Unit', default='L')
    water_duration = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('half_yearly', '6 Months'),
        ('yearly', 'Yearly'),
    ], string='Duration', default='yearly')

    fleet_integration = fields.Boolean(
        string='Fleet Integration',
        default=False,
        help='Integrate fleet with green metrics'
    )
    carbon_limit_notified = fields.Boolean(default=False)

    def write(self, vals):
        """Update company settings and validate the carbon limit when the carbon cap changes."""
        res = super(ResCompany, self).write(vals)
        if 'carbon_cap' in vals:
            for company in self:
                company.check_carbon_limit()
        return res

    @api.model
    def _is_credit_transfer_enabled(self):
        """Return whether buying/selling environmental credits is enabled in settings."""
        param = self.env['ir.config_parameter'].sudo().get_param(
            'cyllo_green_metrics.enable_credit_transfer')
        return str(param).lower() in ('true', '1')

    def check_carbon_limit(self):
        """Validate the company's carbon emissions against the allocated cap and notify users when the limit is exceeded."""
        for company in self:
            today = fields.Date.context_today(company)
            start_date = today.replace(month=1, day=1)
            end_date = today
            calcs = self.env['carbon.calc'].search([
                ('state', 'in', ['approved', 'done']),
                ('date', '>=', start_date),
                ('date', '<=', end_date),
                ('company_id', '=', company.id)
            ])
            air_activities = self.env['carbon.activity'].search([
                ('calculation_id', 'in', calcs.ids),
                ('factor_id.type', '=', 'air')
            ])
            used_amount = sum(activity.emission_total / 1000.0 for activity in air_activities)
            credits = self.env['account.move']._get_available_credits(company.id)
            cap_amount = (company.carbon_cap or 0.0) + credits

            if used_amount > cap_amount:
                if not company.carbon_limit_notified:
                    channel = self.env.ref('mail.channel_general', raise_if_not_found=False)
                    if not channel:
                        channel = self.env['discuss.channel'].search([('name', '=', 'general')], limit=1)
                    cyllobot_partner = self.env.ref('base.partner_root', raise_if_not_found=False) or self.env['res.partner'].search([('name', 'in', ['OdooBot', 'CylloBot'])], limit=1)
                    if self._is_credit_transfer_enabled():
                        closing = _("The limit is over! You can buy credits to increase your cap.")
                    else:
                        closing = _("The limit is over!")
                    body = Markup(
                        _("<b>Carbon Limit Exceeded!</b><br/>"
                        "The carbon emissions (Used: <b>%.3f t CO2e</b>) have exceeded the allocated cap of <b>%.3f t CO2e</b>.<br/>"
                        "%s")
                    ) % (used_amount, cap_amount, closing)
                    if channel:
                        channel.message_post(
                            body=body,
                            message_type='comment',
                            subtype_xmlid='mail.mt_comment',
                            author_id=cyllobot_partner.id if cyllobot_partner else False
                        )
                    user_partner = self.env.user.partner_id
                    if user_partner and cyllobot_partner and user_partner.id != cyllobot_partner.id:
                        chat_channel = self.env['discuss.channel'].channel_get([user_partner.id, cyllobot_partner.id])
                        if chat_channel:
                            chat_channel.message_post(
                                body=body,
                                message_type='comment',
                                subtype_xmlid='mail.mt_comment',
                                author_id=cyllobot_partner.id if cyllobot_partner else False
                            )
                    company.write({'carbon_limit_notified': True})
            else:
                if company.carbon_limit_notified:
                    company.write({'carbon_limit_notified': False})