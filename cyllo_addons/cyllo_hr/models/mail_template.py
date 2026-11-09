# -*- coding: utf-8 -*-
import re

from odoo import api, models

# Odoo palette used by the recruitment emails
ODOO_PURPLE = re.compile(r'#875a7b', re.IGNORECASE)   # "Job Description" button
ODOO_MAUVE = re.compile(r'#9a6c8e', re.IGNORECASE)    # job link and section headings
CYLLO_COLOR = '#9ea700'
CYLLO_TEXT_COLOR = '#838a02'  # darker Cyllo green, readable on white for text

# Recruitment templates to rebrand: "Application Acknowledgement" and "Interest"
RECRUITMENT_TEMPLATES = (
    'hr_recruitment.email_template_data_applicant_congratulations',
    'hr_recruitment.email_template_data_applicant_interest',
)


class MailTemplate(models.Model):
    _inherit = 'mail.template'

    @api.model
    def _cyllo_brand_application_acknowledgement_template(self):
        """Replace the Odoo purple/mauve colours of the recruitment emails by
        Cyllo colours. The base records are noupdate, so they are patched here
        instead of redefined. Safe to run again."""
        for xmlid in RECRUITMENT_TEMPLATES:
            template = self.env.ref(xmlid, raise_if_not_found=False)
            if not template:
                continue
            body = template.body_html or ''
            new_body = ODOO_MAUVE.sub(CYLLO_TEXT_COLOR, ODOO_PURPLE.sub(CYLLO_COLOR, body))
            if new_body != body:
                template.body_html = new_body

    def _register_hook(self):
        # Applies the branding when hr_recruitment is installed, and keeps it
        # if the base template is reset by another module update.
        super()._register_hook()
        self.env['mail.template']._cyllo_brand_application_acknowledgement_template()
