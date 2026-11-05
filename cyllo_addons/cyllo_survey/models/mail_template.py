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
##############################################################################
import re

from odoo import api, models

ODOO_PURPLE = re.compile(r'#875a7b', re.IGNORECASE)  # "Start Survey" / "Start Certification" button
CYLLO_COLOR = '#9ea700'


class MailTemplate(models.Model):
    _inherit = 'mail.template'

    @api.model
    def _cyllo_brand_survey_invite_template(self):
        """Replace the Odoo purple of the "Survey: Invite" email button by the
        Cyllo colour. The survey template is patched here instead of redefined
        so the base file stays untouched. Every installed language is patched,
        English first, so translated emails get the same colour. Safe to run again."""
        template = self.env.ref('survey.mail_template_user_input_invite', raise_if_not_found=False)
        if not template:
            return
        langs = [code for code, _name in self.env['res.lang'].get_installed() if code != 'en_US']
        for lang in ['en_US'] + langs:
            localized = template.with_context(lang=lang)
            body = localized.body_html or ''
            new_body = ODOO_PURPLE.sub(CYLLO_COLOR, body)
            if new_body != body:
                localized.body_html = new_body

    def _register_hook(self):
        # Keeps the branding if the survey module update resets the template.
        super()._register_hook()
        self.env['mail.template']._cyllo_brand_survey_invite_template()
