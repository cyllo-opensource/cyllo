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
import logging
import urllib.parse

import requests

from odoo import fields, models, _

_logger = logging.getLogger(__name__)


class LinkedInOrganization(models.Model):
    """Represents a LinkedIn Company/Organization page linked to a LinkedIn account."""
    _name = 'linkedin.organization'
    _description = 'LinkedIn Organization'
    _order = 'name asc'

    name = fields.Char(string='Name', required=True)
    org_urn = fields.Char(
        string='URN',
        help='LinkedIn URN, e.g. urn:li:organization:123 or urn:li:person:456',
        required=True,
        index=True,
    )
    type = fields.Selection([
        ('person', 'Person'),
        ('organization', 'Organization')
    ], string='Type', default='organization', required=True)
    logo_url = fields.Char(string='Logo URL', help='LinkedIn organization logo URL')
    account_id = fields.Many2one(
        'linkedin.account',
        string='LinkedIn Account',
        required=True,
        ondelete='cascade',
    )
    state = fields.Selection(
        [('active', 'Active'), ('inactive', 'Inactive')],
        default='active',
        string='State',
    )
    followers_count = fields.Integer(string='Total Audience', readonly=True, default=0)

    def action_fetch_audience(self):
        """Fetch this page's follower count via LinkedIn's Network Sizes API
        (rw_organization_admin, already in our OAuth scope - see
        linkedin_account.py's action_connect_linkedin)."""
        self = self.sudo()
        for org in self:
            if org.type != 'organization' or not org.org_urn or not org.account_id.linkedin_access_token:
                continue
            url = f'https://api.linkedin.com/v2/networkSizes/{urllib.parse.quote(org.org_urn, safe="")}'
            headers = {'Authorization': f'Bearer {org.account_id.linkedin_access_token}'}
            try:
                response = requests.get(
                    url, params={'edgeType': 'CompanyFollowedByMember'}, headers=headers, timeout=30)
                data = response.json()
                if 'firstDegreeSize' in data:
                    org.followers_count = data['firstDegreeSize']
                else:
                    _logger.warning("LinkedIn follower count fetch for %s failed: %s", org.name, data)
            except Exception:
                _logger.exception("LinkedIn follower count fetch failed for %s", org.name)

    def action_fetch_feeds(self):
        """Fetch LinkedIn posts for this organization page only."""
        self.ensure_one()
        self = self.sudo()
        account = self.account_id
        if not account.linkedin_access_token:
            return
        legacy_headers = {'Authorization': f'Bearer {account.linkedin_access_token}'}
        count = account._fetch_feeds_for_urn(
            self.org_urn,
            self.name,
            self.logo_url,
            legacy_headers,
            org_id=self.id,
        )
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _(f'{count} new posts synced for {self.name}.'),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_fetch_feed_comments(self, parent_urn):
        """Same V2 comments fetch as linkedin.account's own version - the
        token is account-level regardless of which of its pages is asking."""
        self.ensure_one()
        return self.account_id.action_fetch_feed_comments(parent_urn)

    def action_post_linkedin_comment(self, post_urn, message):
        """Post a top-level comment to a LinkedIn post as THIS specific org -
        unlike linkedin.account's own action_post_linkedin_comment, which has
        to guess "first active org" since it isn't scoped to just one, here
        there's no ambiguity: self.org_urn IS the org actually being posted
        as."""
        self.ensure_one()
        self = self.sudo()
        account = self.account_id
        if not account.linkedin_access_token or not self.org_urn:
            return {'error': 'LinkedIn account not connected or no identity found.'}
        post_urn_encoded = urllib.parse.quote(post_urn)
        v2_url = f"https://api.linkedin.com/v2/socialActions/{post_urn_encoded}/comments"
        headers = {
            'Authorization': f'Bearer {account.linkedin_access_token}',
            'Content-Type': 'application/json',
            'X-Restli-Protocol-Version': '2.0.0',
        }
        body = {
            "actor": self.org_urn,
            "message": {
                "text": message
            }
        }
        try:
            _logger.info(f"V2 POST Request: {v2_url} | Body: {body}")
            res = requests.post(v2_url, json=body, headers=headers, timeout=30)
            _logger.info(f"V2 POST Response: {res.status_code} - {res.text[:200]}")
            if res.status_code in (200, 201):
                return res.json()
            return {'error': res.text}
        except Exception as e:
            _logger.error(f"LinkedIn V2 Post Exception: {str(e)}", exc_info=True)
            return {'error': str(e)}

    def get_org_data(self):
        """Return a dict suitable for the frontend."""
        return {
            'id': self.id,
            'name': self.name,
            'org_urn': self.org_urn,
            'logo_url': self.logo_url or False,
        }
