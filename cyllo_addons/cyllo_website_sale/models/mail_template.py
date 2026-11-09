# -*- coding: utf-8 -*-
import re

from odoo import api, models

ODOO_PURPLE = '#875A7B'
# Previous (broken) expression: {{ }} is not rendered inside a plain style attribute.
BROKEN_EXPRESSION = re.compile(r"\{\{ object\.company_id\.email_secondary_color or (?:'|&#39;)#9ea700(?:'|&#39;) \}\}")
CYLLO_COLOR = '#9ea700'


class MailTemplate(models.Model):
    _inherit = 'mail.template'

    @api.model
    def _cyllo_brand_cart_recovery_template(self):
        """Replace the Odoo purple of the cart recovery email button by the Cyllo
        brand colour. The base record is noupdate, so it is patched here instead
        of being redefined; running it again is harmless."""
        template = self.env.ref('website_sale.mail_template_sale_cart_recovery', raise_if_not_found=False)
        body = template.body_html or '' if template else ''
        new_body = BROKEN_EXPRESSION.sub(CYLLO_COLOR, body).replace(ODOO_PURPLE, CYLLO_COLOR)
        if template and new_body != body:
            template.body_html = new_body

    def _register_hook(self):
        # Keep the branding even if the template is reset by another module update.
        super()._register_hook()
        self.env['mail.template']._cyllo_brand_cart_recovery_template()
