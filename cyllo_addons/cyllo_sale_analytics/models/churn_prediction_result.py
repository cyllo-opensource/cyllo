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
from odoo import models, fields, api
import datetime
import hashlib
import json


class ChurnPredictionResult(models.Model):
    """Per-user/company cache of computed churn results, keyed by a signature of
    the request parameters. Lets the dashboard serve repeat loads instantly
    instead of re-running the (expensive) SQL + ML on every visit."""
    _name = 'churn.prediction.result'
    _description = 'Churn Prediction Result Cache'

    user_id = fields.Many2one('res.users', string='User', required=True,
                              ondelete='cascade', default=lambda self: self.env.user)
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 ondelete='cascade', default=lambda self: self.env.company)
    signature = fields.Char(string='Params Signature', index=True)
    results = fields.Text(string='Results JSON')

    _RESULT_VERSION = 2

    @api.model
    def _signature(self, payload):
        raw = json.dumps({'v': self._RESULT_VERSION, 'params': payload},
                         sort_keys=True, default=str)
        return hashlib.sha1(raw.encode('utf-8')).hexdigest()

    @api.model
    def get_cached(self, payload, max_age_hours=6):
        """Return the cached result dict for `payload`, or None if absent/stale."""
        rec = self.search([
            ('user_id', '=', self.env.user.id),
            ('company_id', '=', self.env.company.id),
            ('signature', '=', self._signature(payload)),
        ], limit=1)
        if not rec or not rec.results:
            return None
        # TTL guard so underlying sales changes eventually force a refresh.
        if rec.write_date and (fields.Datetime.now() - rec.write_date) > \
                datetime.timedelta(hours=max_age_hours):
            return None
        try:
            return json.loads(rec.results)
        except Exception:
            return None

    @api.model
    def store(self, payload, results):
        """Persist `results` for the given `payload` signature (upsert)."""
        def _serial(obj):
            if isinstance(obj, (datetime.date, datetime.datetime)):
                return obj.isoformat()
            return str(obj)
        results_json = json.dumps(results, default=_serial)
        signature = self._signature(payload)
        rec = self.search([
            ('user_id', '=', self.env.user.id),
            ('company_id', '=', self.env.company.id),
            ('signature', '=', signature),
        ], limit=1)
        if rec:
            rec.write({'results': results_json})
        else:
            self.create({
                'user_id': self.env.user.id,
                'company_id': self.env.company.id,
                'signature': signature,
                'results': results_json,
            })
