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
from odoo import fields, models


class UtmCampaign(models.Model):
    """Extends utm.campaign with roll-up stats from this module's social media posts."""
    _inherit = 'utm.campaign'

    social_post_ids = fields.One2many('social.media.post', 'campaign_id', string="Social Media Posts")
    social_post_count = fields.Integer(compute='_compute_social_stats', string="Posts")
    social_total_engagements = fields.Integer(compute='_compute_social_stats', string="Engagements")
    social_leads_created = fields.Integer(compute='_compute_social_stats', string="Leads Created")
    social_leads_converted = fields.Integer(compute='_compute_social_stats', string="Leads Converted")

    def _compute_social_stats(self):
        for campaign in self:
            posts = campaign.social_post_ids
            campaign.social_post_count = len(posts)
            campaign.social_total_engagements = sum(
                getattr(post, 'fb_likes_count', 0) + getattr(post, 'fb_comments_count', 0)
                + getattr(post, 'ig_likes_count', 0) + getattr(post, 'ig_comments_count', 0)
                + getattr(post, 'youtube_likes_count', 0) + getattr(post, 'youtube_comments_count', 0)
                + getattr(post, 'youtube_views_count', 0)
                + getattr(post, 'linkedin_likes_count', 0) + getattr(post, 'linkedin_comments_count', 0)
                for post in posts
            )
            leads = self.env['crm.lead'].sudo().search([('campaign_id', '=', campaign.id)])
            campaign.social_leads_created = len(leads)
            campaign.social_leads_converted = len(leads.filtered(lambda l: l.stage_id.is_won))
