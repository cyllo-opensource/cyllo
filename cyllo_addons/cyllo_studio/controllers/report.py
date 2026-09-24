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
import json
import re
from lxml import etree
from markupsafe import escape

from odoo.http import Controller, route, request
from odoo import fields
from datetime import timedelta


class StudioReportController(Controller):
    """
    A controller for Odoo Studio report, handling saving of modifications.
    """

    def is_studio_user(self):
        studio = request.session.get('studio')
        is_studio_debug = bool(studio) and '1' in studio
        is_studio_user = request.env.user.has_group('cyllo_studio.group_cyllo_studio_user')
        if is_studio_user and not is_studio_debug:
            request.session.studio = '1'
        if not is_studio_user:
            from odoo.exceptions import AccessError
            from odoo import _
            raise AccessError(_("You don't have the access to this request."))

    def is_studio_admin(self):
        self.is_studio_user()
        if not (request.env.user.has_group('cyllo_studio.group_cyllo_studio_admin') or request.env.user.has_group('cyllo_studio.group_cyllo_studio_user')):
            from odoo.exceptions import AccessError
            from odoo import _
            raise AccessError(_("You don't have the admin access to perform this structural change."))
    def _strip_studio_attrs(self, tree):
        """
        Walk every element in *tree* and remove all studio-injected
        attributes that must never appear in saved QWeb templates.
        This is the authoritative server-side cleanup that catches any
        attrs the browser cleanup may have missed.
        """
        REMOVE_ATTRS = {'cy-xpath', 'cy-template', 'cy-type', 'draggable', 'data-cy-new-field'}
        for el in tree.iter():
            for attr in REMOVE_ATTRS:
                el.attrib.pop(attr, None)
            # Strip cursor / outline from inline style
            style = el.get('style', '')
            if style:
                props = [p.strip() for p in style.split(';') if p.strip()]
                clean = [p for p in props
                         if not p.lower().startswith('cursor')
                         and not p.lower().startswith('outline')]
                if clean:
                    el.set('style', '; '.join(clean) + ';')
                else:
                    el.attrib.pop('style', None)

    @route('/cyllo_studio/create/inherited_view', auth="user", csrf=False,
           type='json')
    def create_inherited_view(self, all_arch):
        """
        with open("/tmp/studio_payload.txt", "a") as f:
            f.write("\n\n" + repr(all_arch))
        Create or update inherited QWeb views from the report editor.
        Each item in all_arch has:
          - key:        external ID of the base template
          - xpathBlocks: XML string with <data><xpath ...>...</xpath></data>
        """
        self.is_studio_user()
        try:
            skipped_protected = []
            for arch in all_arch:
                key = arch['key']
                # Guard: never create/modify XPath overrides on protected layout templates.
                # These templates contain t-if/t-else sibling chains that QWeb requires to stay
                # adjacent; any inserted element breaks compilation with:
                #   SyntaxError: t-elif directive must be preceded by t-if or t-elif directive
                if key in self._PROTECTED_LAYOUT_KEYS:
                    # Log a visible warning so this silent-drop is traceable in the server log.
                    # Previously this was a silent continue — save returned {success: True} but
                    # wrote nothing, causing mysterious save-then-revert on reports whose
                    # address/layout zones carry cy-template matching a protected key.
                    import logging as _logging
                    _logging.getLogger(__name__).warning(
                        '[Cyllo Studio] create_inherited_view: skipping protected layout key %r '
                        '— changes targeting this template are silently ignored to prevent '
                        'QWeb t-elif/t-else chain corruption. '
                        'Frontend should anchor new nodes to the document sub-template instead.',
                        key
                    )
                    # Also clean up any accidentally created Custom_ views for this key
                    base_view = request.env.ref(key, raise_if_not_found=False)
                    if base_view:
                        stale = request.env['ir.ui.view'].sudo().search([
                            ('inherit_id', '=', base_view.id),
                            '|', ('name', 'like', 'Custom_'), ('key', 'like', 'Custom_'),
                        ])
                        if stale:
                            stale.unlink()
                    skipped_protected.append(key)
                    continue
                xpath_blocks = re.sub(r'<br\s*>', '<br/>', arch['xpathBlocks'])

                # Fix void HTML elements that XMLSerializer may not self-close
                for tag in ['img', 'input', 'hr', 'link', 'meta']:
                    xpath_blocks = re.sub(
                        rf'<{tag}([^>]*?)(?<!/)>',
                        rf'<{tag}\1/>',
                        xpath_blocks,
                    )

                # Fix double-encoded JSON in t-options generated by JS DOM serialization
                # JS creates: t-options="{&quot;widget&quot;: &quot;contact&quot;}"
                # QWeb needs valid python dicts: t-options='{"widget": "contact"}'
                # ONLY replace if it's inside a t-options block
                xpath_blocks = re.sub(r'(t-options\s*=\s*")([^"]*)(")',
                                      lambda m: m.group(1) + m.group(2).replace('&quot;', "'") + m.group(3),
                                      xpath_blocks)

                # Restore <cy-qweb-t> placeholder tags back to real QWeb <t> tags.
                # The iframe renderer encodes <t> → <cy-qweb-t> so that lxml's HTML
                # parser doesn't strip them; the JS serializer sends them as-is.
                xpath_blocks = re.sub(r'<cy-qweb-t(\s|>|/)', r'<t\1', xpath_blocks)
                xpath_blocks = xpath_blocks.replace('</cy-qweb-t>', '</t>')
                # Parse and validate
                try:
                    arch_el = etree.fromstring(xpath_blocks.encode('utf-8'))

                except etree.XMLSyntaxError as xml_err:
                    return {'success': False,
                            'error': f'Invalid XML in changes: {xml_err}'}

                # ── Strip studio attrs from incoming content ─────────────────
                self._strip_studio_attrs(arch_el)

                for xpath_el in arch_el:
                    position = xpath_el.get('position', '')
                    if position == 'replace':
                        replacement_content = list(xpath_el)
                        for i, node in enumerate(replacement_content):
                            tag = node.tag if isinstance(node.tag, str) else ''
                            if tag == 't':
                                # Check: t-elif / t-else must be immediately preceded by t-if or t-elif
                                if node.get('t-elif') is not None or node.get('t-else') is not None:
                                    prev = replacement_content[i - 1] if i > 0 else None
                                    if prev is None or prev.tag != 't' or (
                                            prev.get('t-if') is None and prev.get('t-elif') is None
                                    ):
                                        return {
                                            'success': False,
                                            'error': (
                                                    'Save rejected: t-elif/t-else node at position %d is not '
                                                    'immediately preceded by t-if or t-elif. '
                                                    'This would cause a QWeb SyntaxError. '
                                                    'Please Reset Report and try again.' % i
                                            )
                                        }

                # Search by KEY, which is much more reliable than name
                custom_arch = request.env['ir.ui.view'].search(
                    [('key', '=', f'Custom_{key}')])

                if custom_arch:
                    try:
                        root = etree.fromstring(custom_arch.arch_base.encode('utf-8'))
                        # Heal any previously saved corruption
                        self._strip_studio_attrs(root)


                        if custom_arch.model:
                            custom_arch.sudo().write({'model': False})

                        
                        if custom_arch.priority != 99:
                            custom_arch.sudo().write({'priority': 99})

                        data_nodes = root.xpath('//data')
                        if not data_nodes:
                            # If for some reason it's missing <data>, wrap it
                            new_root = etree.Element('data')
                            new_root.extend(list(root))
                            root = new_root
                            data_node = root
                        else:
                            data_node = data_nodes[0]

                        processed_xpaths = set()
                        for new_el in arch_el:
                            expr = new_el.get('expr')
                            position = new_el.get('position')
                            if not expr:
                                continue

                            # Deduplicate within the same save operation
                            xpath_key = (expr, position)
                            if xpath_key in processed_xpaths:
                                continue
                            processed_xpaths.add(xpath_key)

                            # Is the incoming node the Cyllo custom footer block?
                            # The footer is re-emitted on *every* save anchored to the
                            # page div (expr=page, position="after"). We must dedupe it
                            # by CONTENT, never by its expr — otherwise the page-anchored
                            # footer would collide with the field xpaths below it.
                            new_el_str = etree.tostring(new_el, encoding='unicode')
                            new_el_is_footer = (
                                'cy-custom-footer' in new_el_str
                                or 'cy-footer-hide-std' in new_el_str
                            )

                            # Purge logic:
                            for old_el in list(root.xpath('//*[@expr]')):
                                old_expr = old_el.get('expr', '')

                                # 0. Footer dedup: when the incoming node is our custom
                                # footer, drop any previously-saved custom-footer xpath
                                # (regardless of its expr/position) so footers do not stack.
                                if new_el_is_footer:
                                    old_el_str = etree.tostring(old_el, encoding='unicode')
                                    if ('cy-custom-footer' in old_el_str
                                            or 'cy-footer-hide-std' in old_el_str):
                                        parentNode = old_el.getparent()
                                        if parentNode is not None:
                                            parentNode.remove(old_el)
                                    # A footer never invalidates field xpaths — skip the
                                    # replace/child-purge rules entirely for it.
                                    continue

                                # 1. If we are REPLACING this exact node, remove the old replacement.
                                if position == 'replace' and old_expr == expr:
                                    parentNode = old_el.getparent()
                                    if parentNode is not None:
                                        parentNode.remove(old_el)

                                # 2. If we are REPLACING this node, any existing XPaths
                                # that target its children are now stale/invalid.
                                # This MUST be gated on position="replace": inserting a
                                # sibling (before/after), inserting inside, or changing
                                # attributes does NOT invalidate the node's descendants.
                                # Previously this fired for every position, so the always
                                # page-anchored footer (position="after") wiped every field
                                # xpath under the page on the 2nd+ save.
                                elif position == 'replace' and old_expr.startswith(expr + '/'):
                                    parentNode = old_el.getparent()
                                    if parentNode is not None:
                                        parentNode.remove(old_el)

                                # 3. Footer-specific: if the same expr is being re-saved with ANY
                                # position (e.g. old "inside" → new "after"), remove the old entry
                                # to avoid stacking duplicate footer blocks.
                                elif old_expr == expr and 'page' in expr.lower():
                                    parentNode = old_el.getparent()
                                    if parentNode is not None:
                                        parentNode.remove(old_el)

                            data_node.append(new_el)
                    except Exception as unexpectedException:
                        # Fallback: just overwrite if merging fails
                        custom_arch.write({'arch_base': xpath_blocks})
                    else:
                        # Only serialize/write the merged tree when the merge
                        # succeeded. Previously this ran unconditionally, so it
                        # clobbered the fallback write and — if the exception
                        # fired before ``root`` was bound — raised NameError that
                        # was swallowed by the outer handler.
                        new_arch = etree.tostring(root, encoding='unicode',
                                                  pretty_print=True)
                        custom_arch.write({'arch_base': new_arch})
                else:
                    base_view = request.env.ref(key, raise_if_not_found=False)
                    if not base_view or not base_view.exists():
                        return {'success': False,
                                'error': f'Base view {key!r} not found'}
                    clean_arch = etree.tostring(arch_el, encoding='unicode',
                                                pretty_print=True)
                    request.env['ir.ui.view'].create({
                        'name': f'Custom_{key}',
                        'key': f'Custom_{key}',
                        'type': 'qweb',
                        'mode': 'extension',
                        'inherit_id': base_view.id,
                        'priority': 99,
                        'arch_base': clean_arch,
                    })
            if skipped_protected:
                return {
                    'success': True,
                    'warning': (
                        'Some changes were skipped because they targeted protected layout '
                        'templates that cannot be safely overridden via XPath inheritance.'
                    ),
                    'skipped_protected': skipped_protected,
                }
            return {'success': True}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    @route('/cyllo_studio/get_arch', auth='user', csrf=False, type='json')
    def get_arch(self, template, show_placeholders=True):
        """
        Re-fetch the rendered report arch for a given template name.
        Called by the frontend when arch is lost after a browser page refresh
        (ir.actions.client params are not persisted across refreshes).
        """
        self.is_studio_user()
        try:
            view = request.env.ref(template)
            if not view.exists():
                return {'success': False, 'error': f'Template {template!r} not found'}

            try:
                arch = view.get_iframe_rendered_template(template, show_placeholders=show_placeholders)
                return {'success': True, 'arch': arch}
            except ValueError as ve:
                # If inheritance is broken, try to purge Custom_ views and retry once
                if "cannot be located in parent view" in str(ve):
                    custom_views = request.env['ir.ui.view'].search([
                        ('inherit_id', '=', view.id),
                        ('name', 'like', 'Custom_'),
                    ])
                    if custom_views:
                        custom_views.unlink()
                        # Retry once
                        arch = view.get_iframe_rendered_template(template, show_placeholders=show_placeholders)
                        return {'success': True, 'arch': arch}
                raise ve

        except Exception as e:
            return {'success': False, 'error': str(e)}

    @route('/cyllo_studio/edit_canvas/<template>', auth='user', type='http')
    def edit_canvas(self, template, **kwargs):
        """
        Return the full rendered HTML document for the Studio editor iframe.
        """
        self.is_studio_user()
        try:
            view = request.env.ref(template, raise_if_not_found=False)
            if not view:
                    return request.make_response("Template not found", status=404)

            html_content = view.get_iframe_rendered_template(template)
            return request.make_response(html_content, headers=[('Content-Type', 'text/html')])
        except Exception as e:
            return request.make_response(f"Error loading canvas: {str(e)}", status=500)

    @route('/cyllo_studio/save_company_footer', type='json', auth='user')
    def save_company_footer(self, company_id, footer_text):
        """Save the company report footer with sudo to prevent access errors."""
        self.is_studio_user()
        try:
            if not request.env.user.has_group('base.group_user'):
                return {'success': False, 'error': 'Unauthorized'}
            company = request.env['res.company'].browse(int(company_id))
            if company.exists():
                company.sudo().write({'report_footer': footer_text})
                return {'success': True}
            return {'success': False, 'error': 'Company not found'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @route('/cyllo_studio/get_footer_preview', auth='user', csrf=False, type='json')
    def get_footer_preview(self):
        """
        Return the rendered footer HTML from web.external_layout_standard for
        display as a static (non-editable) preview strip at the bottom of the
        Cyllo Studio report canvas.

        Uses the raw arch so we can emit human-readable placeholder labels
        (e.g. "Company > Report Footer") rather than trying to evaluate QWeb
        expressions which require a real record context.
        """
        self.is_studio_user()
        try:
            layout = request.env.ref('web.external_layout_standard', raise_if_not_found=False)
            if not layout:
                return {'success': True, 'html': ''}

            arch = layout._get_combined_arch()

            # Strategy 1: div.footer (standard Odoo layout)
            footers = arch.xpath('.//div[contains(@class,"footer")]')
            # Strategy 2: div.o_standard_footer (some community layouts)
            if not footers:
                footers = arch.xpath('.//div[contains(@class,"o_standard_footer")]')
            # Strategy 3: HTML5 <footer> tag
            if not footers:
                footers = arch.xpath('.//footer')
            # Strategy 4: any div that contains a page-number span
            if not footers:
                footers = arch.xpath('.//div[.//span[contains(@class,"page")]]')

            if not footers:
                # Return a minimal hardcoded footer so the frontend always has a strip to show
                fallback_html = (
                    '<div class="o_footer_content">'
                    '<div><span class="cy-footer-placeholder">Company \u203a Report Footer</span></div>'
                    '<div>Page <span class="cy-footer-expr">1</span>'
                    ' / <span class="cy-footer-expr">N</span></div>'
                    '</div>'
                )
                return {'success': True, 'html': fallback_html}

            footer_el = footers[0]

            # Walk the footer tree and replace QWeb expressions with readable labels
            import copy
            footer_copy = copy.deepcopy(footer_el)

            def _humanise(footerNode):
                """Replace t-field / t-out / t-esc with a readable placeholder span."""
                FIELD_MAP = {
                    'company.report_footer': 'Company › Report Footer',
                    'o.name': 'Document Name',
                }

                # t-field → replace with a placeholder chip
                tFieldValue = footerNode.get('t-field')
                if tFieldValue:
                    label = FIELD_MAP.get(tFieldValue.strip(), tFieldValue.strip())
                    footerNode.tag = 'span'
                    footerNode.text = label
                    for attrName in list(footerNode.attrib):
                        del footerNode.attrib[attrName]
                    footerNode.set('class', 'cy-footer-placeholder')
                    return

                # t-out / t-esc → inline expression placeholder
                for attr in ('t-out', 't-esc'):
                    exprValue = footerNode.get(attr)
                    if exprValue is not None:
                        footerNode.tag = 'span'
                        footerNode.text = exprValue.strip()
                        for attrName in list(footerNode.attrib):
                            del footerNode.attrib[attrName]
                        footerNode.set('class', 'cy-footer-expr')
                        return

                # t-if / t-attf-class / t-attf-style → strip qweb attrs
                for attrName in list(footerNode.attrib):
                    if attrName.startswith('t-'):
                        del footerNode.attrib[attrName]

                # <span class="page"/> → "1"  and  <span class="topage"/> → "N"
                cssClasses = footerNode.get('class', '')
                if 'page' in cssClasses.split() and footerNode.tag == 'span':
                    footerNode.text = '1'
                elif 'topage' in cssClasses.split() and footerNode.tag == 'span':
                    footerNode.text = 'N'

                for child in list(footerNode):
                    _humanise(child)

            _humanise(footer_copy)

            html = etree.tostring(footer_copy, encoding='unicode', method='html')
            return {'success': True, 'html': html}

        except Exception as unexpectedException:
            return {'success': False, 'error': str(unexpectedException)}

    @route('/cyllo_studio/get_report_preview_data', auth='user', csrf=False, type='json')
    def get_report_preview_data(self, template, res_model):
        """
        Fetch records, report properties, and available paper formats for the preview sidebar.
        Also includes QR scan analytics summary.
        """
        self.is_studio_user()
        try:
            report = request.env['ir.actions.report'].search([('report_name', '=', template)], limit=1)
            if not report:
                return {'success': False, 'error': f'Report {template!r} not found'}

            # .exists() strips any records whose DB row has been deleted since the search
            records = request.env[res_model].search([], limit=80).exists()

            # Fetch available paper formats with dimensions
            paper_formats = request.env['report.paperformat'].search_read(
                [], ['id', 'name', 'page_width', 'page_height', 'format']
            )

            tokens = request.env['qr.download.token'].sudo().search([('report_id', '=', report.id)])
            total_scans = sum(tokens.mapped('scan_count'))

            recent_scans_data = request.env['qr.scan.event'].sudo().search_read(
                [('report_id', '=', report.id)],
                ['scanned_at', 'ip_address', 'record_id'],
                limit=5,
                order='scanned_at desc'
            )

            # Resolve record names for recent scans
            for scan in recent_scans_data:
                if scan['record_id']:
                    rec = request.env[res_model].sudo().browse(scan['record_id'])
                    scan['record_name'] = rec.display_name if rec.exists() else f"ID: {scan['record_id']}"
                else:
                    scan['record_name'] = "Unknown"

            # Loop variable + whether the report is record-based (see _detect_record_context).
            record_var, record_based = self._detect_record_context(template)

            return {
                'success': True,
                'report': {
                    'id': report.id,
                    'name': report.name,
                    'report_name': report.report_name,
                    'model': report.model,
                    'paperformat_id': report.paperformat_id.id if report.paperformat_id else (request.env.company.paperformat_id.id if request.env.company.paperformat_id else False),
                    'attachment_use': report.attachment_use,
                },
                'pricelist_preview_blocked': bool(
                    (
                        report.report_name in {
                            'product.report_pricelist',
                            'product.report_pricelist_page',
                        }
                        or report.model == 'product.pricelist'
                    )
                    and not request.env.user.has_group('product.group_product_pricelist')
                ),
                'record_ids': records.ids,
                'paper_formats': paper_formats,
                'analytics': {
                    'total_scans': total_scans,
                    'recent_scans': recent_scans_data,
                },
                'record_var': record_var,
                'record_based': record_based,
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @route('/cyllo_studio/render_report_html', auth='user', csrf=False, type='json')
    def render_report_html(self, report_id, doc_ids):
        """
        Return a preview URL for the target report so the frontend can render it
        inside an <iframe src="..."> tag instead of using srcdoc with raw HTML.
        Using Odoo's native /report/html/ route ensures the report is fully styled
        (Odoo asset bundles load correctly) and all QWeb field values are resolved.
        """
        self.is_studio_user()
        try:
            report = request.env['ir.actions.report'].browse(report_id)
            if not report.exists():
                return {'success': False, 'error': 'Report not found'}

            blocked = request.env['ir.actions.report']._get_studio_preview_report_block(report)
            if blocked:
                return blocked

            # Verify that the requested document records still exist in the DB.
            # If the record was deleted after the preview list loaded, .exists()
            # returns an empty recordset — return a structured error so the
            # frontend can skip it gracefully instead of letting a MissingError
            # bubble up as an uncaught exception and an Odoo error page.
            model = report.model
            existing = request.env[model].browse(doc_ids).exists()
            if not existing:
                return {
                    'success': False,
                    'error': 'record_missing',
                    'message': (
                        'The selected record no longer exists in the database. '
                        'It may have been deleted. Skipping to the next record.'
                    ),
                }

            ids_str = ','.join(str(i) for i in existing.ids)
            preview_url = f'/report/html/{report.report_name}/{ids_str}'
            return {'success': True, 'preview_url': preview_url}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @route('/cyllo_studio/generate_qr_token', auth='user', type='json')
    def generate_qr_token(self, template, options):
        """
        Generate a reusable token for a report template.
        """
        self.is_studio_user()
        try:
            report = request.env['ir.actions.report'].search([('report_name', '=', template)], limit=1)
            if not report:
                return {'success': False, 'error': 'Report not found'}

            token_vals = {
                'report_id': report.id,
                'require_auth': options.get('requireAuth', False),
                'track_analytics': options.get('trackAnalytics', True),
            }
            if options.get('expiresDays'):
                token_vals['expires_at'] = fields.Datetime.now() + timedelta(days=int(options['expiresDays']))

            token_record = request.env['qr.download.token'].create(token_vals)
            return {'success': True, 'token': token_record.token}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @route('/report/pdf/<int:report_id>/<int:record_id>', auth='public', methods=['GET'])
    def download_report_pdf(self, report_id, record_id, token=None, **kwargs):
        """
        Download the PDF for a specific report and record using a token.

        This is a public route: authorization is enforced by the token itself
        (existence + ``is_valid()`` below) and by ``require_auth`` (which forces
        login). It must NOT call ``is_studio_user()`` — the QR code is scanned by
        public/portal recipients who are not Studio users, and gating the route
        on that group raised AccessError for exactly its intended audience.
        """
        if not token:
            return request.make_response("Missing token", status=403)

        token_record = request.env['qr.download.token'].sudo().search([
            ('token', '=', token),
            ('report_id', '=', report_id)
        ], limit=1)

        if not token_record or not token_record.is_valid():
            return request.make_response("Invalid or expired link", status=403)

        if token_record.require_auth and not request.session.uid:
            return request.redirect(f'/web/login?redirect=/report/pdf/{report_id}/{record_id}?token={token}')

        report = request.env['ir.actions.report'].sudo().browse(report_id)
        if not report.exists():
            return request.make_response("Report not found", status=404)

        # Track analytics
        if token_record.track_analytics:
            request.env['qr.scan.event'].sudo().create({
                'token_id': token_record.id,
                'record_id': record_id,
                'ip_address': request.httprequest.remote_addr,
                'user_agent': request.httprequest.user_agent.string,
            })
            token_record.sudo().scan_count += 1

        try:
            pdf_content, _ = report.with_context(
                report_pdf_no_attachment=True,
                cyllo_studio_pdf=True,
            )._render_qweb_pdf(report_id, [record_id])

            # Fetch record to build filename
            record = request.env[report.model].sudo().browse(record_id)
            doc_name = record.display_name.replace('/', '_') if record.exists() else str(record_id)
            filename = f"Report_{doc_name}.pdf"

            pdfhttpheaders = [
                ('Content-Type', 'application/pdf'),
                ('Content-Length', len(pdf_content)),
                ('Content-Disposition', f'attachment; filename="{filename}"')
            ]
            return request.make_response(pdf_content, headers=pdfhttpheaders)
        except Exception as e:
            return request.make_response(f"Error generating PDF: {str(e)}", status=500)

    # These are layout wrappers – we skip them when searching for the document template
    _LAYOUT_CALLS = {
        'web.html_container', 'web.external_layout', 'web.external_layout_standard',
        'web.external_layout_boxed', 'web.external_layout_clean', 'web.external_layout_background',
        'web.basic_layout',
    }

    # Layout templates that must NEVER be overridden via custom XPath inheritance.
    # Modifying these breaks the t-if/t-else/t-elif sibling chains in QWeb compilation.
    _PROTECTED_LAYOUT_KEYS = {
        'web.external_layout_standard',
        'web.external_layout_boxed',
        'web.external_layout_bold',
        'web.external_layout_striped',
        'web.external_layout',
        'web.html_container',
        'web.basic_layout',
        'web.internal_layout',
        'web.address_layout',
    }

    @route('/cyllo_studio/cleanup_broken_layout_views', auth='user', csrf=False, type='json')
    def cleanup_broken_layout_views(self):
        """
        Clean up any Custom_ inherited views that target protected layout templates.
        These cause QWeb SyntaxErrors like 't-elif must be preceded by t-if'.
        Call this to repair the database after such an error occurs.
        """
        self.is_studio_user()
        removed = []
        try:
            for key in self._PROTECTED_LAYOUT_KEYS:
                base_view = request.env.ref(key, raise_if_not_found=False)
                if not base_view:
                    continue
                custom_views = request.env['ir.ui.view'].sudo().search([
                    ('inherit_id', '=', base_view.id),
                    '|', ('name', 'like', 'Custom_'), ('key', 'like', 'Custom_'),
                ])
                if custom_views:
                    removed.extend(custom_views.mapped('name'))
                    custom_views.unlink()
            return {'success': True, 'removed': removed}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _resolve_doc_template(self, template):
        """
        Given a wrapper template name (e.g. ``sale.report_saleorder_zew``), walk its
        ``t-call`` children and return the *first* one that is NOT a known layout
        wrapper.  That is the real document template whose arch we want to edit.

        Returns ``(view_record, resolved_template_name)``.
        If no inner call is found, falls back to the wrapper itself.
        """
        try:
            wrapper_view = request.env.ref(template, raise_if_not_found=False)
            if not wrapper_view:
                wrapper_view = request.env['ir.ui.view'].search([('name', '=', template)], limit=1)
            if not wrapper_view or not wrapper_view.exists():
                return None, template

            arch_src = wrapper_view.arch_base or wrapper_view.arch
            if not arch_src:
                return wrapper_view, template

            try:
                root = etree.fromstring(arch_src.encode('utf-8'))
            except etree.XMLSyntaxError:
                return wrapper_view, template

            # Collect all t-call values in document order, skip layout ones
            for el in root.iter():
                t_call = el.get('t-call')
                if t_call and t_call not in self._LAYOUT_CALLS:
                    # Try to resolve this as an external ID
                    doc_view = request.env.ref(t_call, raise_if_not_found=False)
                    if doc_view and doc_view.exists():
                        return doc_view, t_call

            # Nothing found – return the wrapper itself
            return wrapper_view, template
        except Exception:
            return None, template

    def _detect_record_context(self, template):
        """
        Inspect the wrapper template and report whether it renders a *document
        record* and, if so, under which loop variable.

        Returns a ``(record_var, record_based)`` tuple:
          - ``record_var``  – the ``t-as`` name of the ``t-foreach="docs"`` /
            ``t-foreach="doc_ids"`` loop (e.g. ``"o"``), defaulting to ``"doc"``.
          - ``record_based`` – ``True`` only when such a loop actually exists.

        ``record_based`` is the discriminator Studio needs: standard reports
        loop over a recordset, so a dropped field can be bound as
        ``t-field="<record_var>.<field>"``. Custom-data reports — the whole
        family of Cyllo financial reports (Aged, P&L, Trial Balance, Ledgers,
        Tax) that pass hand-built dicts and never expose ``doc`` — have no such
        loop; binding a field to ``doc`` there raises ``KeyError: 'doc'`` at
        render. Those reports must be edited via Edit Sources / QWeb inheritance
        instead, and the editor uses this flag to refuse the drop up front.
        """
        record_var = 'doc'
        record_based = False
        try:
            wrapper_view = request.env.ref(template, raise_if_not_found=False)
            if wrapper_view and wrapper_view.exists():
                wrapper_arch_src = wrapper_view.arch_base or wrapper_view.arch
                if wrapper_arch_src:
                    wrapper_root = etree.fromstring(wrapper_arch_src.encode('utf-8'))
                    for el in wrapper_root.iter():
                        foreach_val = el.get('t-foreach', '')
                        t_as = el.get('t-as', '')
                        if foreach_val in ('docs', 'doc_ids') and t_as:
                            record_var = t_as
                            record_based = True
                            break
        except Exception:
            pass
        return record_var, record_based

    def _get_record_var(self, template):
        """Backward-compatible accessor: the loop variable name only."""
        record_var, _ = self._detect_record_context(template)
        return record_var

    @route('/cyllo_studio/get_report_source', auth='user', csrf=False, type='json')
    def get_report_source(self, template):
        """
        Fetch the raw XML arch of the *document* template (the real content template,
        not the outer wrapper).  Also returns the resolved template name so the
        frontend can pass it back on save.

        Also returns ``record_var``: the name of the foreach loop variable (t-as)
        used in the wrapper template, e.g. ``"o"`` for Employee Resume or ``"doc"``
        for most standard reports. Defaults to ``"doc"`` if not found.
        """
        self.is_studio_user()
        try:
            doc_view, doc_template = self._resolve_doc_template(template)

            if not doc_view or not doc_view.exists():
                return {'success': False, 'error': f'Template {template!r} not found'}

            combined_arch = doc_view._get_combined_arch().xpath('//t[@t-name]')[0]
            arch_xml = etree.tostring(combined_arch, encoding='unicode', pretty_print=True)

            # Detect the record variable name used in the docs foreach loop,
            # and whether the report is record-based at all (see _detect_record_context).
            record_var, record_based = self._detect_record_context(template)

            return {'success': True, 'arch': arch_xml, 'doc_template': doc_template,
                    'record_var': record_var, 'record_based': record_based}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _build_template_payload(self, template):
        report = request.env['ir.actions.report'].sudo().search([('report_name', '=', template)], limit=1)
        if not report:
            raise ValueError(f'Report {template!r} not found')

        doc_view, doc_template = self._resolve_doc_template(template)
        if not doc_view or not doc_view.exists():
            raise ValueError(f'Document template for {template!r} not found')

        wrapper_view = request.env.ref(template, raise_if_not_found=False)
        wrapper_arch = ''
        if wrapper_view and wrapper_view.exists():
            wrapper_arch = etree.tostring(wrapper_view._get_combined_arch(), encoding='unicode', pretty_print=True)

        combined_doc = doc_view._get_combined_arch().xpath('//t[@t-name]')[0]
        document_arch = etree.tostring(combined_doc, encoding='unicode', pretty_print=True)

        paperformat = report.paperformat_id
        payload = {
            'version': 1,
            'source': {
                'report_name': report.report_name,
                'report_model': report.model,
                'document_template': doc_template,
            },
            'architecture': {
                'wrapper_arch': wrapper_arch,
                'document_arch': document_arch,
            },
            'page_settings': {
                'paperformat_id': paperformat.id if paperformat else False,
                'paperformat_name': paperformat.name if paperformat else '',
                'format': paperformat.format if paperformat else '',
                'page_width': paperformat.page_width if paperformat else 0,
                'page_height': paperformat.page_height if paperformat else 0,
                'orientation': paperformat.orientation if paperformat else '',
                'margin_top': paperformat.margin_top if paperformat else 0,
                'margin_bottom': paperformat.margin_bottom if paperformat else 0,
                'margin_left': paperformat.margin_left if paperformat else 0,
                'margin_right': paperformat.margin_right if paperformat else 0,
                'dpi': paperformat.dpi if paperformat else 0,
            },
            'visibility_settings': {
                'attachment_use': bool(report.attachment_use),
                'binding_type': report.binding_type or '',
                'print_report_name': report.print_report_name or '',
            },
            'configuration': {
                'has_qr': 'report-qr' in document_arch or '/report/barcode/' in document_arch,
                'has_tables': '<table' in document_arch,
                'has_signatures': 'o_sign_placeholder' in document_arch or '[[SIGN:' in document_arch,
                'has_sections': 'report-section' in document_arch,
            },
        }
        return report, doc_template, payload

    @route('/cyllo_studio/save_report_template', auth='user', csrf=False, type='json')
    def save_report_template(self, template, name, description='', category=''):
        self.is_studio_admin()
        try:
            name = (name or '').strip()
            if not name:
                return {'success': False, 'error': 'Template Name is required.'}

            report, doc_template, payload = self._build_template_payload(template)
            template_record = request.env['cyllo.report.template'].sudo().create({
                'name': name,
                'description': description or '',
                'category': category or '',
                'source_report_id': report.id,
                'source_model': report.model,
                'source_template': report.report_name,
                'doc_template': doc_template,
                'payload_json': json.dumps(payload, ensure_ascii=False, indent=2),
            })
            return {'success': True, 'template_id': template_record.id}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @route('/cyllo_studio/export_report_template', auth='user', csrf=False, type='json')
    def export_report_template(self, template):
        self.is_studio_admin()
        try:
            report, doc_template, payload = self._build_template_payload(template)
            filename = f"{(report.name or 'report_template').replace('/', '_')}_template.json"
            return {
                'success': True,
                'filename': filename,
                'payload': payload,
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @route('/cyllo_studio/save_report_source', auth='user', csrf=False, type='json')
    def save_report_source(self, template, arch, doc_template=None):
        """
        Save the raw XML arch directly to the document template's inherited view
        (or create one).  ``doc_template`` is the resolved document template name
        returned by ``get_report_source``; if not supplied we fall back to
        auto-detecting it again.
        """
        self.is_studio_admin()
        try:
            # Resolve which template to actually save to
            save_template = doc_template or template
            if not doc_template:
                _, save_template = self._resolve_doc_template(template)

            # Validate XML before saving
            try:
                etree.fromstring(arch.encode('utf-8'))
            except etree.XMLSyntaxError as xml_err:
                return {'success': False, 'error': f'Invalid XML: {xml_err}'}

            # Write directly to the base document view so the PDF immediately
            # reflects the changes (no extra inherited view is created).
            base_view = request.env.ref(save_template, raise_if_not_found=False)
            if not base_view or not base_view.exists():
                # Fall back: search by name
                base_view = request.env['ir.ui.view'].search(
                    [('name', '=', save_template)], limit=1)
            if not base_view or not base_view.exists():
                return {'success': False, 'error': f'View {save_template!r} not found'}

            base_view.write({'arch_base': arch})

            custom_views = request.env['ir.ui.view'].search([
                ('inherit_id', '=', base_view.id),
                ('name', '=', f'Custom_{save_template}'),
            ])
            if custom_views:
                custom_views.sudo().unlink()

            return {'success': True}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _get_all_tcall_targets(self, template_name, max_depth=8):
        """
        Recursively discover all t-call targets reachable from the given template.
        Returns a set of template names.
        """
        cache = set()
        def _traverse(name, depth):
            if depth > max_depth or name in cache:
                return
            cache.add(name)
            view = request.env.ref(name, raise_if_not_found=False)
            if not view:
                return
            try:
                arch = view._get_combined_arch()
            except Exception:
                return
            for node in list(arch.xpath(".//t[@t-call]")):
                called_name = node.get("t-call")
                if not called_name or called_name in self._LAYOUT_CALLS:
                    continue
                _traverse(called_name, depth + 1)
        _traverse(template_name, 0)
        return cache

    @route('/cyllo_studio/check_shared_templates', auth='user', csrf=False, type='json')
    def check_shared_templates(self, templates):
        """
        Check how many top-level reports/actions reference the given templates.
        Returns a list of templates that are shared (referenced by >1 view).
        """
        self.is_studio_user()
        shared = []
        for template in templates:
            callers = request.env['ir.ui.view'].sudo().search_count([
                ('arch_db', 'ilike', f't-call="{template}"')
            ])
            if callers > 1:
                shared.append(template)
        return {'success': True, 'shared_templates': shared}

    @route('/cyllo_studio/reset_report_source', auth='user', csrf=False, type='json')
    def reset_report_source(self, template, include_header_footer=False):
        """
        Reset the document template's arch back to its factory / module defaults
        by calling ir.ui.view.reset_arch(mode='hard').
        """
        self.is_studio_admin()
        try:
            doc_view, doc_template = self._resolve_doc_template(template)
            if not doc_view or not doc_view.exists():
                return {'success': False, 'error': f'View {template!r} not found'}

            if doc_view.key and doc_view.key.startswith('cyllo_studio_custom.'):
                # This is a custom report created by Cyllo Studio. It has no arch_fs, so reset_arch does nothing.
                # We manually restore the blank skeleton.
                model_name = request.env['ir.model'].sudo().search([('model', '=', doc_view.model)], limit=1).name or doc_view.model
                blank_arch = f"""
            <t t-name="{doc_view.key}">
                <t t-call="web.html_container">
                    <t t-call="web.external_layout">
                        <t t-foreach="docs" t-as="doc">
                            <div class="page">
                                <div class="oe_structure"/>
                                <div class="row">
                                    <div class="col-12">
                                        <h2 class="text-center mt-4">
                                            <span t-esc="doc.name or doc.display_name or ''"/>
                                        </h2>
                                        <p class="text-muted text-center">New Report for {escape(model_name)}</p>
                                    </div>
                                </div>
                                <div class="oe_structure"/>
                            </div>
                        </t>
                    </t>
                </t>
            </t>"""
                doc_view.sudo().write({'arch_base': blank_arch})
            else:
                # Hard-reset: restores arch from the module XML file on disk
                doc_view.sudo().reset_arch(mode='hard')

            all_templates = self._get_all_tcall_targets(template)
            all_templates.add(template)

            for tpl in all_templates:
                tpl_view = request.env.ref(tpl, raise_if_not_found=False)
                if not tpl_view:
                    continue
                custom_views = request.env['ir.ui.view'].search([
                    ('inherit_id', 'child_of', tpl_view.id),
                    '|', ('name', 'like', 'Custom_'), ('key', 'like', 'Custom_'),
                ])
                if custom_views:
                    custom_views.sudo().unlink()

            if include_header_footer:
                # Also reset the outer wrapper if it has an arch_fs
                wrapper_view = request.env.ref(template, raise_if_not_found=False)
                if wrapper_view and wrapper_view.exists():
                    if wrapper_view.arch_fs:
                        wrapper_view.sudo().reset_arch(mode='hard')

                    wrapper_custom_views = request.env['ir.ui.view'].search([
                        ('inherit_id', 'child_of', wrapper_view.id),
                        '|', ('name', 'like', 'Custom_'), ('key', 'like', 'Custom_'),
                    ])
                    if wrapper_custom_views:
                        wrapper_custom_views.sudo().unlink()

            fresh_arch = doc_view.arch_base
            return {'success': True, 'arch': fresh_arch}
        except Exception as e:
            return {'success': False, 'error': str(e)}
            if wrapper_view and wrapper_view.exists():
                if wrapper_view.arch_fs:
                    wrapper_view.sudo().reset_arch(mode='hard')

                wrapper_custom_views = request.env['ir.ui.view'].search([
                    ('inherit_id', 'child_of', wrapper_view.id),
                    '|', ('name', 'like', 'Custom_'), ('key', 'like', 'Custom_'),
                ])
                if wrapper_custom_views:
                    wrapper_custom_views.sudo().unlink()

            fresh_arch = doc_view.arch_base
            return {'success': True, 'arch': fresh_arch}
