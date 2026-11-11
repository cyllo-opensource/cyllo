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

import inspect
import logging
import os
import re
from odoo import models, fields, api, _, addons

_logger = logging.getLogger(__name__)


class ErrorReportWizard(models.TransientModel):
    _name = 'error.report.wizard'
    _description = 'Error Report to Admin Wizard'

    name = fields.Char(string='Error Name / Exception', readonly=True)
    error_type = fields.Selection([
        ('backend', 'Python / Backend'),
        ('frontend', 'JavaScript / Frontend'),
        ('xml', 'XML / View / Data'),
        ('warning', 'User Warning / Validation'),
    ], string='Error Type', readonly=True, default='backend')
    module_name = fields.Char(string='Originating Module', readonly=True)
    file_location = fields.Char(string='File / Line', readonly=True)
    error_message = fields.Text(string='Error Message', readonly=True)
    traceback = fields.Text(string='Full Traceback', readonly=True)
    url = fields.Char(string='Page URL', readonly=True)
    user_id = fields.Many2one('res.users', string='Reported By', default=lambda self: self.env.user, readonly=True)
    # NOTE: 'placeholder' is not a field attribute; set it on the field in the form view.
    user_notes = fields.Text(string='Additional Notes')
    attachment = fields.Binary(attachment=True)
    attachment_filename = fields.Char(string="Filename")

    # Framework dispatch / upgrade frames that must NEVER be chosen as the failure root cause
    FRAMEWORK_DISPATCH_PATTERNS = (
        'base/models/ir_module.py',
        'base/models/ir_http.py',
        'web/controllers/dataset.py',
        'web/models/models.py',
        'website/models/ir_http.py',
        'odoo/modules/loading.py',
        'odoo/modules/registry.py',
        'odoo/tools/convert.py',
        'odoo/http.py',
        'odoo/service/model.py',
        'odoo/models.py',
        'odoo/fields.py',
        'odoo/api.py',
    )

    # Exceptions raised on purpose by business rules (configuration / user input problems).
    # When one of these is raised by core code, the raise site is the real origin and
    # custom frames above it are only "involved" in the call path.
    USER_FACING_EXCEPTIONS = (
        'UserError', 'ValidationError', 'AccessError', 'MissingError',
        'RedirectWarning', 'AccessDenied',
    )

    # File "<path>", line N, in <func>\n    <source line>   (source line is optional)
    _FRAME_RE = re.compile(
        r'File "([^"]+)", line (\d+)(?:, in ([^\n\r]+))?'
        r'(?:\r?\n[ \t]+(?!File ")([^\n\r]+))?')
    # Last line of a traceback: "odoo.exceptions.UserError: message"
    _EXC_RE = re.compile(
        r'^(?:[\w.]+\.)?(\w+(?:Error|Exception|Warning|Denied|Exit)):', re.M)

    @api.model
    def _is_framework_js_frame(self, module_name, path):
        """Return True for frames that belong to the JS framework, not to custom code.
        Owl wraps errors, so the stack often contains /web/static/lib/owl/owl.js,
        which says nothing about where the real error was thrown.
        """
        path = path or ''
        module_name = module_name or ''
        if 'static/lib/' in path or module_name in ('web', '@odoo'):
            return True
        # Odoo S.A. modules (web_studio, web_enterprise...) are framework; a CUSTOM
        # module that merely starts with "web_" must not be treated as framework.
        return bool(module_name) and module_name in self._get_core_module_names([module_name])

    @api.model
    def _split_addon_path(self, norm_path):
        """Return (addon_name, sub_path) for a file inside any configured addons path.
        Uses the real addons paths of the running server (odoo.addons.__path__), so
        custom folders with any name are detected. Falls back to a name-based regex.
        """
        for root in sorted(addons.__path__, key=len, reverse=True):
            root = os.path.normpath(root).replace('\\', '/').rstrip('/')
            if norm_path.startswith(root + '/'):
                parts = norm_path[len(root) + 1:].split('/', 1)
                if len(parts) == 2:
                    return parts[0], parts[1]
        match = re.search(
            r'/(?:addons[\w-]*|odoo/addons|custom_addons)/([^/]+)/(.+)$',
            norm_path)
        if match:
            return match.group(1), match.group(2)
        return None, None

    @api.model
    def _get_core_module_names(self, module_names):
        """Return the subset of module_names authored by Odoo S.A. (core / enterprise)."""
        modules = self.env['ir.module.module'].sudo().search(
            [('name', 'in', list(module_names))])
        core = {m.name for m in modules if 'Odoo S.A.' in (m.author or '')}
        # base has no author in some versions; always treat these as core
        return core | ({'base', 'web'} & set(module_names))

    # ------------------------------------------------------------------
    # Origin-frame detection helpers
    # ------------------------------------------------------------------
    @api.model
    def _parse_python_frames(self, traceback_text):
        """Return every Python frame of the traceback, in call order, as dicts:
        {'path', 'line', 'func', 'code'}  ('code' is the source line shown by Python)."""
        return [
            {
                'path': path,
                'line': line_no,
                'func': (func or '').strip(),
                'code': (code or '').strip(),
            }
            for path, line_no, func, code in self._FRAME_RE.findall(traceback_text or '')
        ]

    @api.model
    def _get_exception_name(self, traceback_text):
        """Return the class name of the final exception (e.g. 'UserError'), or ''."""
        matches = self._EXC_RE.findall(traceback_text or '')
        return matches[-1] if matches else ''

    @api.model
    def _is_super_passthrough(self, func_name, code):
        """True for `res = super()._same_method(...)` style delegation frames."""
        if not func_name or not code:
            return False
        return bool(re.search(
            r'\bsuper\(\s*[\w\s,]*\)\s*\.\s*%s\s*\(' % re.escape(func_name), code))

    @api.model
    def _select_origin_frame(self, frames, exception_name, core_modules, last_index):
        """Choose the frame that best represents the origin of the failure.

        :param frames: addon frames (framework dispatch frames already removed) in call
                       order; each a dict with index / addon / sub_path / line / func /
                       passthrough.
        :param exception_name: class name of the final exception.
        :param core_modules: set of addon names authored by Odoo S.A.
        :param last_index: index of the last frame of the whole traceback.
        :return: (primary_frame, via_frame). Both may be None; via_frame is the custom
                 frame that merely sits in the call path of a core raise site.
        """
        custom = [f for f in frames if f['addon'] not in core_modules]
        if not frames or not custom:
            return None, None                      # keep the existing fallbacks
        terminal = frames[-1]
        if terminal['index'] != last_index:
            # The exception was raised in non-addon code (fields.py, sql_db.py ...):
            # keep the previous behaviour (last custom frame).
            return custom[-1], None
        if terminal['addon'] not in core_modules:
            return terminal, None                  # raise site is custom code
        if exception_name in self.USER_FACING_EXCEPTIONS:
            # Core business rule: report the raise site, mention the custom frame as involved
            return terminal, custom[-1]
        # Technical error raised in core: nearest custom caller, skipping pure super() pass-throughs
        real = [f for f in custom if not f['passthrough']]
        return (real or custom)[-1], None

    @api.model
    def _resolve_compute_failure(self, traceback_text):
        """Handle: ValueError: Compute method failed to assign res.users(2,).issue_raised_count
        The error is raised inside odoo/fields.py, after the compute method already
        finished, so the compute method is NOT in the traceback. We read the model and
        field name from the message and find the compute method's source file instead.
        Returns (module_name, location) or (None, None).
        """
        match = re.search(
            r'Compute method failed to assign ([\w.]+)\([^)]*\)\.(\w+)',
            traceback_text or '')
        if not match:
            return None, None
        model_name, field_name = match.groups()
        try:
            model = self.env[model_name]
            field = model._fields[field_name]
            compute = field.compute
            if not compute:
                return None, None
            func = compute if callable(compute) else getattr(type(model), compute, None)
            if func is None:
                return None, None
            func = inspect.unwrap(func)
            src_file = inspect.getsourcefile(func)
            _lines, start_line = inspect.getsourcelines(func)
            module_name, sub_path = self._split_addon_path(src_file.replace('\\', '/'))
            if not module_name:
                return None, None
            return module_name, f"{module_name}/{sub_path}:{start_line} in {func.__name__}()"
        except Exception:
            return None, None

    @api.model
    def _resolve_field_validation_failure(self, traceback_text):
        """Handle: ValueError: Wrong value for partner.transfer.wizard.error_type: 'xml'
        or invalid selection / field type errors raised by the framework during onchange/cache update.
        Returns (module_name, location, error_summary) or (None, None, None).
        """
        if not traceback_text:
            return None, None, None

        # Pattern 1: Wrong value for model(.record)?.field: 'val'
        match = re.search(
            r'Wrong value for ([\w\.]+)(?:\([^)]*\))?\.([\w]+):\s*([^\n\r]+)',
            traceback_text
        )
        if not match:
            # Pattern 2: Field model.field: invalid selection value 'val'
            match = re.search(
                r'(?:Field\s+)?([\w\.]+)(?:\([^)]*\))?\.([\w]+)[:\s]+(?:invalid selection(?: value)?|wrong value)[:\s]+([^\n\r]+)',
                traceback_text,
                re.IGNORECASE
            )

        if not match:
            return None, None, None

        model_name, field_name, invalid_val = match.groups()
        invalid_val_str = invalid_val.strip().strip("'\"")

        module_name = None
        location = None
        error_summary = f"Wrong value for {model_name}.{field_name}: '{invalid_val_str}'"

        # 1. Try resolving model source file in custom addons
        if model_name in self.env:
            try:
                model_cls = type(self.env[model_name])
                src_file = inspect.getsourcefile(model_cls)
                if src_file:
                    norm_path = src_file.replace('\\', '/')
                    mod, sub_path = self._split_addon_path(norm_path)
                    if mod:
                        module_name = mod
                        try:
                            _lines, start_line = inspect.getsourcelines(model_cls)
                            location = f"{mod}/{sub_path}:{start_line} ({model_name}.{field_name}='{invalid_val_str}')"
                        except Exception:
                            location = f"{mod}/{sub_path} ({model_name}.{field_name}='{invalid_val_str}')"
            except Exception:
                pass

        # 2. Try inferring defining module from ir.model.data
        if not module_name and model_name in self.env:
            try:
                ir_model = self.env['ir.model'].sudo().search([('model', '=', model_name)], limit=1)
                if ir_model:
                    data = self.env['ir.model.data'].sudo().search([
                        ('model', '=', 'ir.model'),
                        ('res_id', '=', ir_model.id),
                    ], limit=1)
                    if data and data.module:
                        module_name = data.module
            except Exception:
                pass

        # 3. Clean fallback if no custom source file exists
        if not location:
            location = f"{model_name}.{field_name} (Invalid Value: '{invalid_val_str}')"

        if not module_name:
            module_name = f"Model: {model_name}"

        return module_name, location, error_summary

    @api.model
    def _resolve_xml_parse_failure(self, traceback_text):
        """Extracts custom addon name and file location from Odoo ParseError or View error context."""
        if not traceback_text:
            return None, None

        # Pattern 1: odoo.tools.convert.ParseError: while parsing /path/to/file.xml:121
        parse_match = re.search(
            r'while parsing\s+([^\s,:]+\.(?:xml|csv|sql))(?::(\d+))?',
            traceback_text
        )
        if parse_match:
            file_path, line_no = parse_match.groups()
            norm_path = file_path.replace('\\', '/')
            addon_name, sub_path = self._split_addon_path(norm_path)
            if addon_name:
                loc = f"{addon_name}/{sub_path}:{line_no}" if line_no else f"{addon_name}/{sub_path}"
                return addon_name, loc

        # Pattern 2: View error context: {'file': '/path/to/file.xml', 'line': 10}
        ctx_match = re.search(
            r"View error context:[\s\S]*?'file':\s*['\"]([^'\"]+)['\"](?:[\s\S]*?'line':\s*(\d+))?",
            traceback_text
        )
        if ctx_match:
            file_path, line_no = ctx_match.groups()
            norm_path = file_path.replace('\\', '/')
            addon_name, sub_path = self._split_addon_path(norm_path)
            if addon_name:
                loc = f"{addon_name}/{sub_path}:{line_no}" if line_no else f"{addon_name}/{sub_path}"
                return addon_name, loc

        return None, None

    @api.model
    def count_my_reports(self):
        """Number of issue reports created by the current user.
        Called by the JS before/after the wizard to detect that a report was really
        created (so debug=assets can be switched off again). sudo(): the user may not
        have read access on issue.report.
        """
        return self.env['issue.report'].sudo().search_count(
            [('user_id', '=', self.env.user.id)])

    @api.model
    def _resolve_qweb_failure(self, traceback_text):
        """Handle QWebException ("Error while render the template ... Template: x.y").
        The Python frames only show ir_qweb.py (framework); the real culprit is the
        template/view named in the message.
        Returns (module_name, location) or (None, None).
        """
        if not traceback_text or 'Error while render' not in traceback_text:
            return None, None
        tmpl_match = re.search(r'Template:\s*([\w.\-]+)', traceback_text)
        if not tmpl_match:
            return None, None
        tmpl = tmpl_match.group(1)
        path_match = re.search(r'Path:\s*(\S+)', traceback_text)
        node_path = f" @ {path_match.group(1)}" if path_match else ''
        try:
            View = self.env['ir.ui.view'].sudo()
            view = View.browse(int(tmpl)) if tmpl.isdigit() else View.env.ref(
                tmpl, raise_if_not_found=False)
            arch_fs = (view.arch_fs or '') if view and view._name == 'ir.ui.view' else ''
        except Exception:
            arch_fs = ''
        module_name = arch_fs.split('/')[0] if arch_fs else (
            tmpl.split('.')[0] if '.' in tmpl else None)
        if not module_name:
            return None, None
        return module_name, f"{arch_fs or tmpl} (QWeb template {tmpl}{node_path})"

    @api.model
    def _resolve_sql_failure(self, traceback_text):
        """Handle psycopg2 integrity errors (unique / not-null / foreign key / check).
        The raising frame is odoo/sql_db.py, so frame based detection is useless.
        Constraint names are mapped through ir.model.constraint to module + model.
        Returns (module_name, location, summary) or (None, None, None).
        """
        if not traceback_text:
            return None, None, None
        constraint = re.search(
            r'violates (unique|foreign key|check|exclusion) constraint "([^"]+)"',
            traceback_text)
        if constraint:
            kind, cname = constraint.groups()
            try:
                rec = self.env['ir.model.constraint'].sudo().search(
                    [('name', '=', cname)], limit=1)
                if rec:
                    module = rec.module.name if rec.module else None
                    model = rec.model.model if rec.model else ''
                    return (module or f"Model: {model}",
                            f"{model} ({kind} constraint '{cname}')",
                            f"{kind.capitalize()} constraint violated: {cname}")
            except Exception:
                _logger.debug("Constraint lookup failed", exc_info=True)
            return None, None, f"{kind.capitalize()} constraint violated: {cname}"
        notnull = re.search(
            r'null value in column "([^"]+)"(?: of relation "([^"]+)")? violates not-null',
            traceback_text)
        if notnull:
            column, table = notnull.groups()
            model_name = next(
                (name for name, cls in self.env.registry.items()
                 if getattr(cls, '_table', None) == table), None)
            summary = f"Required value missing: {table + '.' if table else ''}{column}"
            return (f"Model: {model_name}" if model_name else None,
                    f"{model_name or table}.{column} (NOT NULL)", summary)
        return None, None, None

    @api.model
    def default_get(self, fields_list):
        """Function for extracting the path and file names from an error """
        res = super(ErrorReportWizard, self).default_get(fields_list)
        ctx = self.env.context
        traceback_text = res.get('traceback') or ctx.get('default_traceback') or ''
        url = res.get('url') or ctx.get('default_url') or ''

        # Use pre-resolved values from context if provided by frontend
        preset_module = ctx.get('default_module_name')
        preset_location = ctx.get('default_file_location')
        preset_type = ctx.get('default_error_type')

        # Clean framework presets so traceback is parsed accurately below
        if preset_location and (
            'static/lib/' in preset_location
            or preset_location.startswith(('web/', '@odoo/'))
            or any(p in preset_location for p in self.FRAMEWORK_DISPATCH_PATTERNS)
        ):
            preset_location = None
            preset_module = None
        elif preset_module in ('web', '@odoo', 'base'):
            preset_module = None
            preset_location = None

        # An unknown type would make default_get itself raise "Wrong value for ...error_type"
        valid_types = dict(self._fields['error_type'].selection)
        if preset_type not in valid_types:
            preset_type = None

        extracted_module = preset_module
        extracted_location = preset_location
        error_type = preset_type or 'backend'

        # -------------------------------------------------------------
        # 1. PRIORITY 1: Explicit XML ParseError / View Validation Check
        # -------------------------------------------------------------
        xml_module, xml_location = self._resolve_xml_parse_failure(traceback_text)
        if not xml_location:
            xml_module, xml_location = self._resolve_qweb_failure(traceback_text)
        if xml_location:
            extracted_module = xml_module
            extracted_location = xml_location
            error_type = 'xml'

        # 2. PRIORITY 2: Python Backend Traceback Parsing

        elif 'Traceback (most recent call last):' in traceback_text or 'File "' in traceback_text:
            error_type = 'backend'

            python_frames = re.findall(
                r'File "([^"]+)", line (\d+)(?:, in ([^\n\r]+))?',
                traceback_text
            )

            # A. Check for custom addon frames first
            addon_frame_candidates = []
            if python_frames:
                for file_path, line_no, func_name in python_frames:
                    norm_path = file_path.replace('\\', '/')
                    addon_name, sub_path = self._split_addon_path(norm_path)
                    if addon_name:
                        addon_frame_candidates.append(
                            (addon_name, sub_path, line_no, func_name, norm_path)
                        )

            core_modules = self._get_core_module_names({c[0] for c in addon_frame_candidates}) if addon_frame_candidates else set()

            # Exclude framework dispatcher frames (web/models/models.py, ir_module.py, etc.)
            non_dispatch_candidates = [
                c for c in addon_frame_candidates
                if not any(pattern in c[4] for pattern in self.FRAMEWORK_DISPATCH_PATTERNS)
            ]

            # 1. Select the true origin frame.
            #    Instead of blindly taking "the last custom frame in the stack", look at
            #    the frame that actually raised and at the exception type:
            #      - raise site in custom code            -> that frame
            #      - core raise site + UserError & co.    -> core raise site, custom frame as "called via"
            #      - core raise site + technical error    -> nearest custom caller (skipping super() pass-throughs)
            #      - raised outside addons (fields.py...) -> last custom frame (previous behaviour)
            exception_name = self._get_exception_name(traceback_text)
            parsed_frames = self._parse_python_frames(traceback_text)
            origin_frames = []
            for idx, frame in enumerate(parsed_frames):
                norm_path = frame['path'].replace('\\', '/')
                if any(pattern in norm_path for pattern in self.FRAMEWORK_DISPATCH_PATTERNS):
                    continue
                addon_name, sub_path = self._split_addon_path(norm_path)
                if addon_name:
                    origin_frames.append(dict(
                        frame,
                        index=idx,
                        addon=addon_name,
                        sub_path=sub_path,
                        passthrough=self._is_super_passthrough(frame['func'], frame['code']),
                    ))

            primary_frame, via_frame = self._select_origin_frame(
                origin_frames, exception_name, core_modules, len(parsed_frames) - 1)

            if primary_frame and not extracted_location:
                extracted_module = primary_frame['addon']
                func_str = f" in {primary_frame['func']}()" if primary_frame['func'] else ""
                extracted_location = (
                    f"{primary_frame['addon']}/{primary_frame['sub_path']}"
                    f":{primary_frame['line']}{func_str}"
                )
                if via_frame:
                    via_func = f" in {via_frame['func']}()" if via_frame['func'] else ""
                    extracted_location += (
                        f" [called via {via_frame['addon']}/{via_frame['sub_path']}"
                        f":{via_frame['line']}{via_func}]"
                    )

            # 2. Check for Compute method failures
            if not extracted_location:
                compute_module, compute_location = self._resolve_compute_failure(traceback_text)
                if compute_location:
                    extracted_module = compute_module
                    extracted_location = compute_location

            # 2b. SQL integrity errors (unique / not-null / FK / check)
            if not extracted_location:
                sql_module, sql_location, sql_summary = self._resolve_sql_failure(traceback_text)
                if sql_location:
                    extracted_module = sql_module
                    extracted_location = sql_location
                    if not res.get('name') or res.get('name') in ('Server Error', 'IntegrityError'):
                        res['name'] = sql_summary

            # 3. Check for Field / Selection Validation failures (e.g. Wrong value for partner.transfer.wizard.error_type: 'xml')
            if not extracted_location:
                val_module, val_location, val_summary = self._resolve_field_validation_failure(traceback_text)
                if val_location:
                    extracted_module = val_module
                    extracted_location = val_location
                    if not res.get('name') or res.get('name') in ('Server Error', 'ValueError'):
                        res['name'] = val_summary

            # 4. Fallback to non-dispatch framework candidate if present
            if not extracted_location and non_dispatch_candidates:
                mod_name, sub_path, line_no, func_name, _ = non_dispatch_candidates[-1]
                extracted_module = mod_name
                func_str = f" in {func_name.strip()}()" if func_name else ""
                extracted_location = f"{mod_name}/{sub_path}:{line_no}{func_str}"

            # 5. Clean generic fallback without blaming 'web'
            elif not extracted_location and python_frames:
                last_file, line_no, func_name = python_frames[-1]
                norm_path = last_file.replace('\\', '/')
                filename = norm_path.split('/')[-1]
                func_str = f" in {func_name.strip()}()" if func_name else ""
                extracted_location = f"{filename}:{line_no}{func_str}"
                extracted_module = 'Odoo ORM / Validation'


        # 3. PRIORITY 3: JavaScript Frontend Traceback Parsing

        else:
            if not preset_type:
                error_type = 'frontend'

            # A. Source-mapped JS frame: e.g. (/addon_name/static/src/js/file.js:123) or (@addon_name/static/...)
            annotated_matches = re.findall(
                r'(?:\((?:https?://[^/]+)?(?:\/|@)([\w_]+)\/(static\/[^\s():]+):(\d+)(?::\d+)?\)|(?:@|\/)([\w_]+)\/(static\/[^\s():]+):(\d+))',
                traceback_text
            )

            if annotated_matches and (not extracted_location or not extracted_module):
                for match in annotated_matches:
                    # Tuple groups depending on regex branch
                    mod_name = match[0] or match[3]
                    file_subpath = match[1] or match[4]
                    line_no = match[2] or match[5]
                    if not (mod_name and file_subpath):
                        continue
                    if self._is_framework_js_frame(mod_name, file_subpath):
                        continue
                    if not extracted_module:
                        extracted_module = mod_name
                    if not extracted_location:
                        extracted_location = f"{mod_name}/{file_subpath}:{line_no}"
                    break

            # B. Raw unmapped JS bundle fallback: e.g. web.assets_web.min.js:2892:45
            if not extracted_location:
                js_raw_matches = re.findall(
                    r'(?:https?://[^()\s]+/)?([^/\s()]+\.js):(\d+)(?::(\d+))?',
                    traceback_text
                )
                js_raw_matches = [m for m in js_raw_matches if m[0] not in ('owl.js',)]
                if js_raw_matches:
                    bundle_file, line_no, col_no = js_raw_matches[0]
                    col_str = f":{col_no}" if col_no else ""
                    extracted_location = f"[Bundled Asset] {bundle_file}:{line_no}{col_str}"
                    if not extracted_module:
                        extracted_module = 'web / assets'

        # 4. Fallbacks

        if not extracted_module:
            model_match = re.search(r'model=([\w\.]+)', url)
            if model_match:
                extracted_module = f"Model: {model_match.group(1)}"
            else:
                extracted_module = 'Unknown / Core'

        if not extracted_location:
            extracted_location = 'N/A'

        res['module_name'] = extracted_module
        res['file_location'] = extracted_location
        # UserError/ValidationError/RedirectWarning dialogs are always "warning"
        res['error_type'] = 'warning' if preset_type == 'warning' else error_type
        return res

    def action_send_report(self):
        """Create the Issue Report and show a success notification with a
        clickable reference. The form view opens only when the link is clicked."""
        self.ensure_one()
        try:
            with self.env.cr.savepoint():
                issue_record = self.env['issue.report'].sudo().create({
                    'name': self.name or _('Unnamed Error'),
                    'error_type': self.error_type,
                    'module_name': self.module_name,
                    'file_location': self.file_location,
                    'error_message': self.error_message,
                    'traceback': self.traceback,
                    'url': self.url,
                    'company_id': self.env.company.id,
                    'user_id': self.env.user.id,
                    'user_notes': self.user_notes,
                    'state': 'draft',
                    'is_readonly': True,
                })
                if self.attachment:
                    attachment = self.env['ir.attachment'].sudo().create({
                        'name': self.attachment_filename or f"Attachment_{issue_record.id}.png",
                        'type': 'binary',
                        'datas': self.attachment,
                        'res_model': 'issue.report',
                        'res_id': issue_record.id,
                    })
                    issue_record.message_post(
                        body=_("User attached a file with this report."),
                        attachment_ids=[attachment.id],
                    )
        except Exception:

            _logger.exception("Could not create issue.report from error.report.wizard")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Report Not Submitted'),
                    'message': _(
                        'Your issue could not be recorded. Please try again later.'),
                    'type': 'danger',
                    'sticky': False,
                    'next': {'type': 'ir.actions.act_window_close'},
                },
            }

        return {
            'type': 'ir.actions.client',
            'tag': 'issue_report_notification',
            'params': {
                'title': _('Report Submitted'),
                'message': _('Your issue has been recorded.'),
                'issue_id': issue_record.id,
                'issue_ref': issue_record.issue_ref,
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }